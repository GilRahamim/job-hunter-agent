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
from jobhunter.collectors.details import fetch_posting, linkedin_job_id
from jobhunter.dedupe import dedupe_batch, is_new
from jobhunter.filters import (filter_jobs, junior_reason, junior_signals, keyword_hits, required_years,
                               years_over_limit)
from jobhunter.matcher import llm_score, prescore, preferences_text
from jobhunter.models import CandidateProfile, Job, JobMatch

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
    choices: str = ""                                            # jobs the user pursued / dismissed
    scorer: Any = None                                           # chat model behind the pipeline's scoring prompt
    candidates: dict[str, Job] = field(default_factory=dict)     # new jobs that passed the filters
    prescores: dict[str, float] = field(default_factory=dict)
    read: dict[str, int] = field(default_factory=dict)           # id -> tool turn it was read in
    turn: int = 0                                                # tool turns so far (set by the graph)
    closed: set[str] = field(default_factory=set)                # LinkedIn: no longer accepting applications
    over_years: set[str] = field(default_factory=set)            # the scorer read too many required years
    matches: dict[str, dict] = field(default_factory=dict)       # id -> {"score", "reason", "match"}
    score_errors: list[str] = field(default_factory=list)
    cache: dict[str, list[Job]] = field(default_factory=dict)    # fixed-list source -> jobs
    health: list[dict] = field(default_factory=list)
    drop_reasons: Counter = field(default_factory=Counter)
    searches: int = 0                                            # searches charged to max_searches
    collected: int = 0
    group_searches: Counter = field(default_factory=Counter)     # role group -> searches
    dry_groups: set[str] = field(default_factory=set)            # no strong match in recent runs: 1 search
    query_log: list[dict] = field(default_factory=list)          # one entry per search that ran
    found_by: dict[str, int] = field(default_factory=dict)       # id -> index in query_log

    @property
    def settings(self) -> dict[str, Any]:
        return self.config["agent"]

    def strong_matches(self) -> int:
        return sum(1 for m in self.matches.values()
                   if m["score"] is not None and m["score"] >= self.settings["min_match_score"])

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


COVERAGE_NOTE = " Role groups not searched yet: {todo}. Cover them before repeating a group."


def coverage_note(ctx: AgentContext) -> str:
    groups = ctx.settings.get("role_groups") or {}
    todo = [g for g in groups if not ctx.group_searches[g]]
    if not todo:
        return ""
    return COVERAGE_NOTE.format(todo=", ".join(todo))


def group_cap(ctx: AgentContext, group: str) -> int:
    """Searches one role group may use this run: one for a dry group, max_searches_per_group otherwise."""
    return 1 if group in ctx.dry_groups else ctx.settings.get("max_searches_per_group",
                                                               ctx.settings["max_searches"])


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
    fresh = [j for j in dedupe_batch(jobs)
             if j.id not in ctx.candidates and is_new(j, ctx.known_ids, ctx.known_keys)]
    return filter_jobs(fresh, ctx.config)


def _add_candidate(ctx: AgentContext, job: Job, score: float) -> None:
    """Remember a new job; its company|title key hides the same role on other sources later this run."""
    ctx.candidates[job.id] = job
    ctx.prescores[job.id] = score
    ctx.found_by[job.id] = len(ctx.query_log) - 1
    if job.company.strip():
        ctx.known_keys.add(job.dedupe_key)


def is_free(ctx: AgentContext, source: str) -> bool:
    """Title-matched sources cost nothing once their list is loaded, so those searches are not
    charged to max_searches; every linkedin search and each first load are."""
    return source not in QUERY_SOURCES and source in ctx.cache


# ------------------------------------------------------------ tool bodies

def get_profile(ctx: AgentContext) -> str:
    p = ctx.profile
    return "\n".join([
        f"Headline: {p.headline or '-'}",
        f"Seniority: {p.seniority} ({p.years_experience:g} years professional experience)",
        f"Skills: {', '.join(p.skills[:40]) or '-'}",
        f"Target roles: {', '.join(p.target_roles) or '-'}",
        f"Projects: {'; '.join(p.projects[:6]) or '-'}",
    ]) + preferences_text(ctx.config) + ctx.choices


def search_jobs(ctx: AgentContext, query: str, source: str) -> str:
    query = query.strip()
    sources = allowed_sources(ctx.config)
    if source not in sources:
        return f"ERROR: unknown source {source!r}. Use one of: {', '.join(sources)}."
    if not query:
        return "ERROR: query is empty."
    free = is_free(ctx, source)
    if not free and ctx.searches >= ctx.settings["max_searches"]:
        loaded = ", ".join(s for s in sources if is_free(ctx, s))
        still_free = f" Searches on {loaded} are still free." if loaded else ""
        return (f"Search budget used up.{still_free} Read and save the best candidates you already found, "
                "then stop.")
    groups = ctx.settings.get("role_groups") or {}
    hit = query_groups(query, groups)
    if hit and all(ctx.group_searches[g] >= group_cap(ctx, g) for g in hit):
        dry = " (dry: no strong match in recent runs)" if all(g in ctx.dry_groups for g in hit) else ""
        return (f"ERROR: role group {' / '.join(hit)} already has {ctx.group_searches[hit[0]]} "
                f"searches{dry}.{coverage_note(ctx) or ' Search a different kind of job.'}")
    searched = junior_query(ctx, query) if source in QUERY_SOURCES else query
    ctx.searches += 0 if free else 1
    ctx.group_searches.update(hit)
    found = _fetch(ctx, source, searched)
    kept, dropped = _new_and_filtered(ctx, found)
    ctx.drop_reasons.update(dropped)
    scores = prescore(ctx.profile, kept)
    ctx.query_log.append({"query": query, "source": source, "found": len(found), "new": len(kept)})
    for job, score in zip(kept, scores):
        _add_candidate(ctx, job, score)
    ranked = sorted(zip(kept, scores), key=lambda p: p[1], reverse=True)
    top = ranked[: ctx.settings["results_per_search"]]
    head = (f"{f'Searched as {searched!r} (junior roles only). ' if searched != query else ''}"
            f"{len(found)} postings matched, {len(kept)} new after filters"
            f"{' (dropped: ' + ', '.join(f'{k} {v}' for k, v in dropped.items()) + ')' if dropped else ''}. "
            f"{'This search was free (list already loaded). ' if free else ''}"
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
    first_read = job.id not in ctx.read
    ctx.read.setdefault(job.id, ctx.turn)
    if first_read and linkedin_job_id(job.url):   # the page says whether it still accepts applications
        posting = fetch_posting(job)
        job.description = job.description.strip() or posting.description
        if posting.closed:
            ctx.closed.add(job.id)
            ctx.drop_reasons["closed"] += 1
    if job.id in ctx.closed:
        return (f"CLOSED: {job.title} @ {job.company} is no longer accepting applications on LinkedIn. "
                "Do not save it; find another job.")
    years = required_years(f"{job.title}\n{job.description}")
    remote = f" (remote; region: {job.remote_region or 'unspecified'})" if job.is_remote else ""
    text = job.description[: ctx.settings["max_posting_chars"]] or "(no description available)"
    return (f"Title: {job.title}\nCompany: {job.company}\nLocation: {job.location or '-'}{remote}\n"
            f"Posted: {job.date_posted or 'unknown'}\n"
            f"Stated years of experience: {f'{years:g}' if years else 'none stated'}\n"
            f"Junior signals: {', '.join(junior_signals(job, _junior_words(ctx))) or 'none'}\n"
            f"Description:\n{text}")


def score_job(ctx: AgentContext, job: Job) -> JobMatch | None:
    """The pipeline's scoring prompt and rubric (matcher.llm_score), so agent picks and pipeline jobs
    are scored the same way. None when there is no scorer or every retry failed."""
    if ctx.scorer is None:
        return None
    return llm_score(ctx.scorer, ctx.profile, [job], ctx.config, ctx.score_errors, ctx.choices)[0]


def save_match(ctx: AgentContext, job_id: str, reason: str) -> str:
    job = ctx.candidates.get(job_id.strip())
    if job is None:
        return "ERROR: unknown job_id. Use an id from search_jobs results."
    if job.id not in ctx.read:
        return "ERROR: call read_posting on this job before saving it."
    if job.id in ctx.over_years:
        return f"REFUSED: {job.title} @ {job.company} asks for too much experience. Find another job."
    if job.id in ctx.closed:                                 # guardrail: open jobs only
        return f"REFUSED: {job.title} @ {job.company} is no longer accepting applications. Do not save it."
    not_junior = junior_reason(job, ctx.config)              # guardrail: junior roles only
    if not_junior:
        ctx.drop_reasons[f"save_refused_{not_junior}"] += 1
        return (f"REFUSED: {job.title} @ {job.company} is not a junior role ({not_junior}). "
                "The candidate wants junior / entry-level jobs only. Do not save it; find another job.")
    if ctx.read[job.id] == ctx.turn:                         # read and saved in one batch: never seen
        return ("ERROR: you read this posting in this same turn, so you have not seen its text yet. "
                "Judge it from the read_posting result, then save it in your next turn.")
    match = score_job(ctx, job)
    if match and years_over_limit(job, match.required_years, ctx.config):   # same backstop as the pipeline
        ctx.drop_reasons["save_refused_experience_llm"] += 1
        ctx.over_years.add(job.id)
        return (f"REFUSED: the scorer read {match.required_years:g} required years of experience in "
                f"{job.title} @ {job.company}; the candidate is junior. Find another job.")
    ctx.matches[job.id] = {"score": match.score if match else None, "reason": reason.strip(), "match": match}
    s = ctx.settings
    progress = f"Matches at or above {s['min_match_score']}: {ctx.strong_matches()}/{s['goal_matches']}."
    if match is None:
        return (f"Saved {job.title} @ {job.company}, but the scorer failed, so it does not count "
                f"toward the goal. {progress}")
    gaps = f" Missing: {', '.join(match.missing_skills[:4])}." if match.missing_skills else ""
    return (f"Saved {job.title} @ {job.company}. Scorer: {match.score} ({match.verdict}).{gaps} {progress}")


# ------------------------------------------------------------ tool schemas

class SearchArgs(BaseModel):
    query: str = Field(description="Job title or keywords, e.g. 'Junior Python Developer'", max_length=80)
    source: str = Field(description="Where to search; one of the sources listed in the instructions")


class ReadArgs(BaseModel):
    job_id: str = Field(description="An id from search_jobs results")


class SaveArgs(BaseModel):
    job_id: str = Field(description="An id from search_jobs results that you have read")
    reason: str = Field(description="One sentence: why this job is worth applying to", max_length=600)


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
            lambda job_id, reason: save_match(ctx, job_id, reason), name="save_match",
            args_schema=SaveArgs,
            description="Save a junior job you read in an earlier turn. A scorer rates it 0-100 with a "
                        "fixed rubric and returns the score. Jobs that require experience are refused."),
    ]
