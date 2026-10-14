"""Tools the agent model can call. The model decides *what* to search and *which* jobs to save;
dedupe, the rule filters and the budgets stay here, outside its control."""
from __future__ import annotations

import copy
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from jobhunter.collectors import collect_all
from jobhunter.collectors.details import fetch_description
from jobhunter.filters import filter_jobs, junior_reason, junior_signals, keyword_hits, required_years
from jobhunter.matcher import prescore
from jobhunter.models import CandidateProfile, Job

log = logging.getLogger(__name__)

# tool-facing source name -> registry names. Only "linkedin" searches by query; the others
# fetch their full lists once per run and the query is matched against job titles.
AGENT_SOURCES: dict[str, list[str]] = {
    "linkedin": ["jobspy"],
    "company_pages": ["ats", "techmap", "getro"],
    "remote_boards": ["remotive", "remoteok", "himalayas", "arbeitnow", "weworkremotely"],
}
QUERY_SOURCES = {"linkedin"}
_CONFIG_KEY = {"jobspy": "jobspy", "ats": "company_boards", "remotive": "remotive",
               "remoteok": "remoteok", "himalayas": "himalayas", "arbeitnow": "arbeitnow",
               "weworkremotely": "weworkremotely", "techmap": "techmap",
               "getro": "getro"}


@dataclass
class AgentContext:
    """Everything the tools share during one agent run."""
    config: dict[str, Any]
    profile: CandidateProfile
    known_ids: set[str]
    known_keys: set[str]
    candidates: dict[str, Job] = field(default_factory=dict)     # new jobs that passed the filters
    prescores: dict[str, float] = field(default_factory=dict)
    read: set[str] = field(default_factory=set)
    matches: dict[str, dict] = field(default_factory=dict)       # id -> {"score", "reason"}
    cache: dict[str, list[Job]] = field(default_factory=dict)    # fixed-list source -> jobs
    health: list[dict] = field(default_factory=list)
    drop_reasons: Counter = field(default_factory=Counter)
    searches: int = 0
    collected: int = 0
    group_searches: Counter = field(default_factory=Counter)     # role group -> searches

    @property
    def settings(self) -> dict[str, Any]:
        return self.config["agent"]

    def strong_matches(self) -> int:
        return sum(1 for m in self.matches.values() if m["score"] >= self.settings["min_match_score"])

    def goal_reached(self) -> bool:
        return self.strong_matches() >= self.settings["goal_matches"]


_WORD = re.compile(r"[\w֐-׿+#]+")


def _words(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def query_groups(query: str, groups: dict[str, list[str]]) -> list[str]:
    """Role groups a query belongs to: its words cover a group title, or a title covers its words
    ("data analyst" -> Data; short board queries like "data" or "ai" -> every group with that word)."""
    q = _words(query) - {"junior", "jr", "entry", "level", "graduate", "student"}
    if not q:
        return []
    return [g for g, titles in groups.items()
            if any((t := _words(title)) and (t <= q or q <= t) for title in titles)]


def coverage_note(ctx: AgentContext) -> str:
    groups = ctx.settings.get("role_groups") or {}
    todo = [g for g in groups if not ctx.group_searches[g]]
    if not todo:
        return ""
    return f" Role groups not searched yet: {', '.join(todo)}. Cover them before repeating a group."


def allowed_sources(config: dict[str, Any]) -> list[str]:
    """Tool source names that are listed under agent.sources and enabled under sources."""
    enabled = config.get("sources", {})
    out = []
    for name in config["agent"].get("sources", list(AGENT_SOURCES)):
        regs = AGENT_SOURCES.get(name, [])
        if any((enabled.get(_CONFIG_KEY[r]) or {}).get("enabled", False) for r in regs):
            out.append(name)
    return out


def _junior_words(ctx: AgentContext) -> list[str]:
    return ctx.config["filters"].get("junior_keywords") or []


def junior_query(ctx: AgentContext, query: str) -> str:
    """Guardrail: query-searched sources only get junior queries ("AI Engineer" -> "Junior AI Engineer")."""
    prefix = (ctx.settings.get("junior_query_prefix") or "").strip()
    if not prefix or keyword_hits(query, _junior_words(ctx)):
        return query
    return f"{prefix} {query}"


# ------------------------------------------------------------ fetching

def _fetch(ctx: AgentContext, source: str, query: str) -> list[Job]:
    cfg = ctx.config
    if source in QUERY_SOURCES:
        cfg = copy.deepcopy(cfg)
        cfg["search"]["queries"] = [query]
        cfg["search"]["results_per_query"] = ctx.settings["search_limit"]
        if "fetch_linkedin_descriptions" in ctx.settings:      # needed to check experience requirements
            cfg["sources"]["jobspy"]["fetch_linkedin_descriptions"] = bool(
                ctx.settings["fetch_linkedin_descriptions"])
        results, health = collect_all(cfg, AGENT_SOURCES[source])
        ctx.health.extend(health)
        jobs = [j for r in results for j in r.jobs]
        ctx.collected += len(jobs)
        return jobs
    if source not in ctx.cache:
        enabled = cfg.get("sources", {})
        regs = [r for r in AGENT_SOURCES[source] if (enabled.get(_CONFIG_KEY[r]) or {}).get("enabled")]
        results, health = collect_all(cfg, regs)          # full list once; the query filters titles
        ctx.health.extend(health)
        ctx.cache[source] = [j for r in results for j in r.jobs]
        ctx.collected += len(ctx.cache[source])
    words = _WORD.findall(query.lower())
    # "Junior AI Engineer" must still find "AI Engineer": the junior check runs in the filters,
    # so junior words only narrow the title match when the query has nothing else ("Student").
    junior = {w for k in _junior_words(ctx) for w in _WORD.findall(k.lower())}
    words = [w for w in words if w not in junior] or words
    return [j for j in ctx.cache[source] if title_matches(j.title, words)]


def title_matches(title: str, words: list[str]) -> bool:
    """Every query word starts a word of the title: "engineer" hits "Engineering",
    but "ai" does not hit "Retail" or "Maintenance"."""
    title_words = _WORD.findall(title.lower())
    return all(any(t.startswith(w) for t in title_words) for w in words)


def _new_and_filtered(ctx: AgentContext, jobs: list[Job]) -> tuple[list[Job], Counter]:
    from jobhunter.agent import dedupe_batch          # late import: agent.py imports the collectors too

    fresh = [j for j in dedupe_batch(jobs)
             if j.id not in ctx.known_ids and j.id not in ctx.candidates
             and (not j.company.strip() or j.dedupe_key not in ctx.known_keys)]
    return filter_jobs(fresh, ctx.config)


# ------------------------------------------------------------ tool bodies

def get_profile(ctx: AgentContext) -> str:
    p = ctx.profile
    return "\n".join([
        f"Headline: {p.headline or '-'}",
        f"Seniority: {p.seniority} ({p.years_experience:g} years professional experience)",
        f"Skills: {', '.join(p.skills[:40]) or '-'}",
        f"Target roles: {', '.join(p.target_roles) or '-'}",
        f"Projects: {'; '.join(p.projects[:6]) or '-'}",
    ])


def search_jobs(ctx: AgentContext, query: str, source: str) -> str:
    query = query.strip()
    sources = allowed_sources(ctx.config)
    if source not in sources:
        return f"ERROR: unknown source {source!r}. Use one of: {', '.join(sources)}."
    if not query:
        return "ERROR: query is empty."
    if ctx.searches >= ctx.settings["max_searches"]:
        return ("Search budget used up. Read and save the best candidates you already found, "
                "then stop.")
    groups = ctx.settings.get("role_groups") or {}
    hit = query_groups(query, groups)
    cap = ctx.settings.get("max_searches_per_group", ctx.settings["max_searches"])
    if hit and all(ctx.group_searches[g] >= cap for g in hit):
        return (f"ERROR: role group {' / '.join(hit)} already has {cap} searches."
                f"{coverage_note(ctx) or ' Search a different kind of job.'}")
    searched = junior_query(ctx, query) if source in QUERY_SOURCES else query
    ctx.searches += 1
    ctx.group_searches.update(hit)
    found = _fetch(ctx, source, searched)
    kept, dropped = _new_and_filtered(ctx, found)
    ctx.drop_reasons.update(dropped)
    scores = prescore(ctx.profile, kept)
    for job, score in zip(kept, scores):
        ctx.candidates[job.id] = job
        ctx.prescores[job.id] = score
    ranked = sorted(zip(kept, scores), key=lambda p: p[1], reverse=True)
    top = ranked[: ctx.settings["results_per_search"]]
    head = (f"{f'Searched as {searched!r} (junior roles only). ' if searched != query else ''}"
            f"{len(found)} postings matched, {len(kept)} new after filters"
            f"{' (dropped: ' + ', '.join(f'{k} {v}' for k, v in dropped.items()) + ')' if dropped else ''}. "
            f"Searches left: {ctx.settings['max_searches'] - ctx.searches}.{coverage_note(ctx)}")
    if not top:
        hint = " Try a broader or different query." if source not in QUERY_SOURCES else ""
        return head + hint
    lines = [f"{j.id} | {j.title} | {j.company} | {j.location or j.remote_region or '-'} | fit {s:.0f}"
             f" | {', '.join(junior_signals(j, _junior_words(ctx))[:3]) or '-'}"
             for j, s in top]
    return (head + "\nid | title | company | location | fit (keyword pre-score 0-100) | junior signals\n"
            + "\n".join(lines))


def read_posting(ctx: AgentContext, job_id: str) -> str:
    job = ctx.candidates.get(job_id.strip())
    if job is None:
        return "ERROR: unknown job_id. Use an id from search_jobs results."
    ctx.read.add(job.id)
    if not job.description.strip():               # LinkedIn / Tech Map jobs: read the posting now
        job.description = fetch_description(job)
    years = required_years(f"{job.title}\n{job.description}")
    remote = f" (remote; region: {job.remote_region or 'unspecified'})" if job.is_remote else ""
    text = job.description[: ctx.settings["max_posting_chars"]] or "(no description available)"
    return (f"Title: {job.title}\nCompany: {job.company}\nLocation: {job.location or '-'}{remote}\n"
            f"Posted: {job.date_posted or 'unknown'}\n"
            f"Stated years of experience: {f'{years:g}' if years else 'none stated'}\n"
            f"Junior signals: {', '.join(junior_signals(job, _junior_words(ctx))) or 'none'}\n"
            f"Description:\n{text}")


def save_match(ctx: AgentContext, job_id: str, score: int, reason: str) -> str:
    job = ctx.candidates.get(job_id.strip())
    if job is None:
        return "ERROR: unknown job_id. Use an id from search_jobs results."
    if job.id not in ctx.read:
        return "ERROR: call read_posting on this job before saving it."
    not_junior = junior_reason(job, ctx.config)              # guardrail: junior roles only
    if not_junior:
        ctx.drop_reasons[f"save_refused_{not_junior}"] += 1
        return (f"REFUSED: {job.title} @ {job.company} is not a junior role ({not_junior}). "
                "The candidate wants junior / entry-level jobs only. Do not save it; find another job.")
    ctx.matches[job.id] = {"score": score, "reason": reason.strip()}
    s = ctx.settings
    return (f"Saved {job.title} @ {job.company} with score {score}. "
            f"Matches at or above {s['min_match_score']}: {ctx.strong_matches()}/{s['goal_matches']}.")


# ------------------------------------------------------------ tool schemas

class SearchArgs(BaseModel):
    query: str = Field(description="Job title or keywords, e.g. 'Junior Python Developer'", max_length=80)
    source: str = Field(description="Where to search; one of the sources listed in the instructions")


class ReadArgs(BaseModel):
    job_id: str = Field(description="An id from search_jobs results")


class SaveArgs(BaseModel):
    job_id: str = Field(description="An id from search_jobs results that you have read")
    score: int = Field(ge=0, le=100, description="Fit for this candidate, 0-100")
    reason: str = Field(description="One or two sentences: why it fits and the main gap", max_length=600)


class NoArgs(BaseModel):
    pass


def make_tools(ctx: AgentContext) -> list[StructuredTool]:
    """Bind the tool bodies to this run's context."""
    return [
        StructuredTool.from_function(
            lambda: get_profile(ctx), name="get_profile", args_schema=NoArgs,
            description="Return the candidate's profile: seniority, skills and target roles."),
        StructuredTool.from_function(
            lambda query, source: search_jobs(ctx, query, source), name="search_jobs",
            args_schema=SearchArgs,
            description="Search one source for new junior / entry-level job postings. Returns ids, titles, "
                        "a keyword pre-score and junior signals. Location, seniority and experience "
                        "filters are already applied."),
        StructuredTool.from_function(
            lambda job_id: read_posting(ctx, job_id), name="read_posting", args_schema=ReadArgs,
            description="Read a posting's full text, its stated years of experience and junior signals."),
        StructuredTool.from_function(
            lambda job_id, score, reason: save_match(ctx, job_id, score, reason), name="save_match",
            args_schema=SaveArgs,
            description="Save a junior job you have read as a match with your score and reason. "
                        "Jobs that require experience are refused."),
    ]
