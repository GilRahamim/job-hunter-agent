"""Memory across agent runs: which queries led to saved jobs. Each run stores its per-query results
in its stats (`runs.stats.queries`); the next run's start message summarizes the last few runs."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from jobhunter import db
from jobhunter.agent_loop.tools import AgentContext, query_groups
from jobhunter.prompts import AGENT_MEMORY

RUNS_SCANNED = 50          # recent runs looked at to find the last agent runs (pipeline runs are mixed in)
MAX_LINES = 8              # per list: queries that worked, queries that found nothing


def query_stats(ctx: AgentContext) -> list[dict]:
    """Per search of this run: what it found, and how many of its jobs were read / saved / strong."""
    out = [{**q, "read": 0, "saved": 0, "strong": 0} for q in ctx.query_log]
    for job_id, i in ctx.found_by.items():
        if job_id in ctx.read:
            out[i]["read"] += 1
        m = ctx.matches.get(job_id)
        if m:
            out[i]["saved"] += 1
            out[i]["strong"] += (m["score"] or 0) >= ctx.settings["min_match_score"]
    return out


def agent_runs(n_runs: int, path: str | Path | None = None) -> list[dict]:
    """The last `n_runs` agent runs that stored their per-query results, newest first."""
    if n_runs <= 0:
        return []
    return [r for r in db.last_runs(RUNS_SCANNED, path) if "queries" in r["stats"]][:n_runs]


def group_history(n_runs: int, groups: dict[str, list[str]],
                  path: str | Path | None = None) -> dict[str, dict[str, int]]:
    """Per role group over the last `n_runs` agent runs: searches, saved and strong jobs.
    Groups never searched are left out."""
    out: dict[str, dict[str, int]] = {}
    for r in agent_runs(n_runs, path):
        for q in r["stats"]["queries"]:
            for g in query_groups(q["query"], groups):
                h = out.setdefault(g, {"searches": 0, "saved": 0, "strong": 0})
                h["searches"] += 1
                h["saved"] += q.get("saved", 0)
                h["strong"] += q.get("strong", 0)
    return out


def dry_groups(history: dict[str, dict[str, int]], min_searches: int) -> set[str]:
    """Groups searched at least `min_searches` times recently without one strong match (0 = off)."""
    if min_searches <= 0:
        return set()
    return {g for g, h in history.items() if h["searches"] >= min_searches and not h["strong"]}


def past_queries(n_runs: int, path: str | Path | None = None) -> tuple[int, list[dict]]:
    """(agent runs found, per query+source totals over the last `n_runs` agent runs), best first."""
    runs = agent_runs(n_runs, path)
    totals: dict[tuple[str, str], dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "new": 0, "saved": 0, "strong": 0})
    for r in runs:
        for q in r["stats"]["queries"]:
            t = totals[(q["query"].strip().lower(), q["source"])]
            t.update(query=q["query"], source=q["source"])
            for k in ("new", "saved", "strong"):
                t[k] += q.get(k, 0)
            t["runs"] += 1
    rows = sorted(totals.values(), key=lambda t: (-t["strong"], -t["saved"], -t["new"]))
    return len(runs), rows


def _line(t: dict) -> str:
    return (f'- "{t["query"]}" on {t["source"]}: searched {t["runs"]}x, {t["new"]} new jobs, '
            f'{t["saved"]} saved ({t["strong"]} strong)')


def memory_text(n_runs: int, path: str | Path | None = None) -> str:
    """The AGENT_MEMORY block for the start message, or "" when there is no agent history."""
    runs, rows = past_queries(n_runs, path)
    if not rows:
        return ""
    worked = [t for t in rows if t["saved"]][:MAX_LINES]
    empty = [t for t in rows if not t["saved"]][-MAX_LINES:]
    return AGENT_MEMORY.format(runs=runs,
                               worked="\n".join(map(_line, worked)) or "- none yet",
                               empty="\n".join(map(_line, empty)) or "- none")
