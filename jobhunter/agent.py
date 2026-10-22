"""The search pipeline as a fixed LangGraph: load_profile -> collect -> dedupe -> filter -> prescore
-> (llm_score) -> save. Nodes are thin wrappers; the logic lives in collectors/filters/matcher/db."""
from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from jobhunter import db, stop
from jobhunter.collectors import collect_all
from jobhunter.collectors.base import CollectorResult
from jobhunter.collectors.details import fill_descriptions
from jobhunter.config import load_config
from jobhunter.cv import load_profile as load_cv_profile
from jobhunter.db import job_from_row
from jobhunter.dedupe import dedupe_batch, is_new
from jobhunter.filters import filter_jobs, junior_reason, over_limit_score, years_limit, years_over_limit
from jobhunter.llm import get_llm
from jobhunter.matcher import llm_score as score_with_llm
from jobhunter.matcher import prescore as prescore_jobs
from jobhunter.matcher import choices_text, scored_row, select_for_llm
from jobhunter.models import CandidateProfile, Job, JobMatch
from jobhunter.notify import notify_strong_matches
from jobhunter.personalize import personalize

log = logging.getLogger(__name__)


class PipelineState(TypedDict, total=False):
    config: dict
    options: dict                  # no_llm, sources, limit, rescore, dry_run, db_path
    llm: Any
    llm_enabled: bool
    model: str
    run_id: int | None
    started: float
    profile: CandidateProfile
    cv_hash: str
    raw_jobs: list[Job]
    health: list[dict]
    results: list[CollectorResult]
    new_jobs: list[Job]
    known_ids: list[str]
    kept_jobs: list[Job]
    drop_reasons: dict[str, int]
    to_score: list[Job]            # new kept jobs + re-scored jobs from the DB
    rescored_ids: set[str]
    prescores: list[float]
    matches: dict[str, JobMatch | None]
    llm_error: str | None
    rows: list[dict]
    stats: dict


# ------------------------------------------------------------ helpers

def _db(state: PipelineState) -> str | None:
    return state["options"].get("db_path")


# ------------------------------------------------------------ nodes

def load_profile_node(state: PipelineState) -> dict:
    cfg, opts = state["config"], state["options"]
    llm = None if opts.get("no_llm") else get_llm(cfg)
    profile, cv_hash, hit = load_cv_profile(cfg, llm, _db(state))
    cfg = personalize(cfg, profile)          # auto_from_cv users: search terms from their CV
    run_id = None if opts.get("dry_run") else db.start_run(_db(state))
    opts["_run_id"] = run_id          # so run() can close the row if a later node crashes
    model = cfg["llm"]["model"]
    log.info("mode: %s | profile: %d skills, %s (cache %s)",
             f"LLM ({model})" if llm else "heuristic only", len(profile.skills), profile.seniority,
             "hit" if hit else "miss")
    return {"config": cfg, "llm": llm, "llm_enabled": llm is not None, "model": model, "profile": profile,
            "cv_hash": cv_hash, "run_id": run_id, "started": time.monotonic()}


def collect_node(state: PipelineState) -> dict:
    opts = state["options"]
    only = opts.get("sources") or None
    results, health = collect_all(state["config"], only, opts.get("limit"))
    jobs = [j for r in results for j in r.jobs]
    for h in health:
        log.info("source %-15s %4d jobs %5.1fs %s", h["source"], h["fetched"], h["duration_s"] or 0,
                 f"ERROR: {h['error']}" if h["error"] else f"note: {h['warning']}" if h.get("warning") else "")
    return {"results": results, "health": health, "raw_jobs": jobs}


def dedupe_node(state: PipelineState) -> dict:
    ids, keys = db.existing_ids_and_keys(_db(state))
    unique = dedupe_batch(state["raw_jobs"])
    known = [j.id for j in unique if j.id in ids]
    new = [j for j in unique if is_new(j, ids, keys)]
    if known and not state["options"].get("dry_run"):
        db.touch_seen(known, _db(state))
    log.info("dedupe: %d raw -> %d unique, %d already known, %d new", len(state["raw_jobs"]),
             len(unique), len(known), len(new))
    return {"new_jobs": new, "known_ids": known}


def filter_node(state: PipelineState) -> dict:
    cfg = state["config"]
    kept, dropped = filter_jobs(state["new_jobs"], cfg)
    # Jobs without a description (LinkedIn, Tech Map) cannot be checked for experience: read the
    # descriptions of the most promising ones, then apply the experience rules again. LinkedIn jobs
    # that no longer accept applications are dropped too.
    limit = int(cfg["matching"].get("fetch_descriptions") or 0)
    bare = [j for j in kept if not j.description.strip()]
    if limit and bare:
        ranked = [j for _, j in sorted(zip(prescore_jobs(state["profile"], bare), bare),
                                       key=lambda p: p[0], reverse=True)]
        closed = fill_descriptions(ranked, limit)
        failed = {j.id: "closed" for j in bare if j.id in closed}
        failed |= {j.id: r for j in bare
                   if j.id not in failed and j.description and (r := junior_reason(j, cfg))}
        kept = [j for j in kept if j.id not in failed]
        dropped.update(failed.values())
    log.info("filter: kept %d, dropped %s", len(kept), dict(dropped) or "none")
    return {"kept_jobs": kept, "drop_reasons": dict(dropped)}


def prescore_node(state: PipelineState) -> dict:
    cfg, opts = state["config"], state["options"]
    m = cfg["matching"]
    to_score = list(state["kept_jobs"])
    rescored: set[str] = set()
    if opts.get("rescore") or m.get("rescore_on_cv_change") or state["llm_enabled"]:
        rows = db.jobs_needing_rescore(
            state["cv_hash"], None, _db(state), force=bool(opts.get("rescore")),
            include_heuristic=state["llm_enabled"], min_prescore=m["min_prescore_for_llm"])
        have = {j.id for j in to_score}
        for row in rows:
            if len(rescored) >= m["llm_top_n"]:
                break
            job = job_from_row(row)
            # stored before the junior filters (or before they were tightened): do not score it again.
            # Filter before capping, or non-junior rows would fill every slot run after run.
            if row["id"] not in have and junior_reason(job, cfg) is None:
                to_score.append(job)
                rescored.add(row["id"])
        if rescored:
            log.info("rescore: %d existing jobs queued", len(rescored))
    scores = prescore_jobs(state["profile"], to_score)
    return {"to_score": to_score, "prescores": scores, "rescored_ids": rescored}


def after_prescore(state: PipelineState) -> str:
    if stop.stop_requested():
        log.info("stop requested: skipping LLM scoring, saving what was collected")
        return "save"
    return "llm_score" if state["llm_enabled"] and state["to_score"] else "save"


def llm_score_node(state: PipelineState) -> dict:
    picks = select_for_llm(state["prescores"], state["config"])
    jobs = [state["to_score"][i] for i in picks]
    log.info("llm: scoring %d of %d jobs", len(jobs), len(state["to_score"]))
    errors: list[str] = []
    n = int(state["config"]["matching"].get("feedback_examples") or 0)
    choices = choices_text(db.status_examples(n, _db(state)))      # learn from the user's own statuses
    results = score_with_llm(state["llm"], state["profile"], jobs, state["config"], errors, choices)
    if errors:
        log.error("llm: %d of %d jobs could not be scored, e.g. %s", len(errors), len(jobs), errors[0])
    return {"matches": {j.id: r for j, r in zip(jobs, results)}, "llm_error": errors[0] if errors else None}


def save_node(state: PipelineState) -> dict:
    matches = state.get("matches", {})
    rows, drop_reasons = [], dict(state["drop_reasons"])
    for j, pre in zip(state["to_score"], state["prescores"]):
        row = scored_row(j, pre, matches.get(j.id), state["cv_hash"], state["model"])
        # The LLM read an experience requirement the rules missed: do not add the job. A job already
        # in the DB (rescored) keeps its row, with the new years and a capped score (the rubric's
        # seniority rule allows ~2 years over, so it can still score 75), and the dashboard hides it.
        if years_over_limit(j, row["required_years"], state["config"]):
            if j.id not in state["rescored_ids"]:
                drop_reasons["experience_llm"] = drop_reasons.get("experience_llm", 0) + 1
                continue
            row["score"] = over_limit_score(row["score"], row["required_years"],
                                            years_limit(j, state["config"]))
        rows.append(row)
    opts = state["options"]
    stats = {
        "mode": f"llm:{state['model']}" if state["llm_enabled"] else "heuristic",
        "collected": len(state["raw_jobs"]), "new": len(state["new_jobs"]),
        "known": len(state["known_ids"]), "filtered_by_reason": drop_reasons,
        "kept": len(state["kept_jobs"]), "rescored": len(state["rescored_ids"]),
        "prescored": len(rows), "llm_scored": sum(1 for m in matches.values() if m),
        "llm_failed": sum(1 for m in matches.values() if m is None),
        "llm_error": state.get("llm_error"),
        "errors": [f"{h['source']}: {h['error']}" for h in state["health"] if h["error"]],
        "duration_s": round(time.monotonic() - state["started"], 1),
        "dry_run": bool(opts.get("dry_run")),
    }
    if not opts.get("dry_run"):
        db.upsert_jobs(rows, _db(state))
        db.finish_run(state["run_id"], stats, state["health"], _db(state))
    log.info("saved %d jobs%s | %s", len(rows), " (dry run: nothing written)" if opts.get("dry_run") else "",
             stats["mode"])
    return {"rows": rows, "stats": stats}


def notify_node(state: PipelineState) -> dict:
    if state["options"].get("dry_run"):
        return {}
    notify_strong_matches(state["rows"], state["config"])
    return {}


def build_graph():
    g = StateGraph(PipelineState)
    for name, fn in [("load_profile", load_profile_node), ("collect", collect_node),
                     ("dedupe", dedupe_node), ("filter", filter_node), ("prescore", prescore_node),
                     ("llm_score", llm_score_node), ("save", save_node), ("notify", notify_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "load_profile")
    g.add_edge("load_profile", "collect")
    g.add_edge("collect", "dedupe")
    g.add_edge("dedupe", "filter")
    g.add_edge("filter", "prescore")
    g.add_conditional_edges("prescore", after_prescore, {"llm_score": "llm_score", "save": "save"})
    g.add_edge("llm_score", "save")
    g.add_edge("save", "notify")
    g.add_edge("notify", END)
    return g.compile()


# ------------------------------------------------------------ run

def run(config: dict[str, Any] | None = None, **options: Any) -> PipelineState:
    """Run the pipeline once. Options: no_llm, sources, limit, rescore, dry_run, db_path."""
    state: PipelineState = {"config": config or load_config(), "options": options}
    app = build_graph()
    try:
        return app.invoke(state)
    except Exception as e:
        log.exception("run crashed")
        if options.get("_run_id"):
            db.finish_run(options["_run_id"], {"error": f"{type(e).__name__}: {e}"}, [], options.get("db_path"))
        raise RuntimeError(f"pipeline crashed: {e}") from e
