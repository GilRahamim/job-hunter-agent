---
name: agent-pipeline
description: The LangGraph orchestration of the Job Hunter project — graph state, nodes (load_profile, collect, dedupe, filter, prescore, llm_score, save), the conditional LLM edge, run statistics, logging, the run_agent.py CLI flags. Use this whenever working on jobhunter/agent.py, run_agent.py, adding a pipeline step, or when a run hangs, crashes, or reports odd stats.
---

# Agent pipeline

A fixed LangGraph `StateGraph`. It's a graph rather than a plain function so steps are explicit, individually testable, observable (LangSmith tracing works for free if `LANGSMITH_API_KEY` is set), and easy to extend with new nodes (e.g. a "draft cover letter" node later).

## State

```python
class PipelineState(TypedDict, total=False):
    config: dict
    options: dict                 # CLI flags: no_llm, sources, limit, rescore, dry_run
    run_id: int
    profile: CandidateProfile
    cv_hash: str
    raw_jobs: list[Job]
    health: list[dict]            # per-source {source, fetched, error, duration_s}
    new_jobs: list[Job]           # after dedupe vs DB and within batch
    kept_jobs: list[Job]          # after filters
    drop_reasons: dict[str, int]
    prescores: dict[str, float]   # job.id -> prescore
    matches: dict[str, JobMatch]  # job.id -> LLM result
    stats: dict
```

Nodes return partial dicts (LangGraph merges them). Keep each node a thin wrapper that calls the real logic in `collectors/`, `filters.py`, `matcher.py`, `db.py` — the logic stays testable without the graph.

## Graph

```python
g = StateGraph(PipelineState)
g.add_node("load_profile", load_profile)   # cv.get_profile(); start_run()
g.add_node("collect", collect)             # collectors.collect_all() in parallel
g.add_node("dedupe", dedupe)               # vs DB ids/keys + within batch; touch_seen() for known
g.add_node("filter", filter_jobs)          # filters.apply(); record drop_reasons
g.add_node("prescore", prescore)           # + add jobs_needing_rescore() when CV changed
g.add_node("llm_score", llm_score)
g.add_node("save", save)                   # upsert_jobs(); finish_run(stats, health)

g.add_edge(START, "load_profile")
g.add_edge("load_profile", "collect")
g.add_edge("collect", "dedupe")
g.add_edge("dedupe", "filter")
g.add_edge("filter", "prescore")
g.add_conditional_edges("prescore", lambda s: "llm_score" if s.get("llm_enabled") else "save")
g.add_edge("llm_score", "save")
g.add_edge("save", END)
app = g.compile()
```

`llm_enabled` = `get_llm(config) is not None and not options.no_llm`. Decide it once in `load_profile` and put it in state; log which mode the run is in.

`load_profile` also returns `config`: for `auto_from_cv` users (people added from the dashboard) `personalize(cfg, profile)` swaps in search titles, role keywords and the experience limit derived from their CV, so every later node uses those. The run lock lives in `jobhunter/runlock.py` (`run_lock`, `running_pid`, `lock_path(user)`), dedupe in `jobhunter/dedupe.py`; `agent.py` holds only the graph.

Jobs dropped by filters are **not** saved (keeps the DB focused); their counts are in `stats.filtered_by_reason`. If the owner wants to audit drops, add a `--save-dropped` flag that writes them with `status='not_relevant'` and `verdict='filtered:<reason>'`.

## CLI — `run_agent.py`
| Flag | Effect |
|---|---|
| *(none)* | full run |
| `--no-llm` | heuristic scores only |
| `--sources ats,remotive` | only these collectors (names from the registry) |
| `--limit N` | cap jobs per source (fast dev loops) |
| `--rescore` | re-score all non-rejected jobs against the current CV (still bounded by `llm_top_n` per run) |
| `--dry-run` | run everything but don't write to the DB; print the top 15 |
| `--check-companies` | run `scripts/check_boards.py` and exit |

End of run: print a compact summary — per-source counts/errors, filter drops, number scored, and the top 10 new jobs (`score | title | company | location`). Exit code 0 even if some sources failed; non-zero only if the run itself crashed or *every* source failed.

## Logging
`logging` to console (INFO) and `data/logs/run-YYYYMMDD-HHMM.log` (DEBUG). Silence noisy libraries (`urllib3`, `httpx`, JobSpy's own logger to WARNING). Never log API keys or full CV text.

## Concurrency
- Collectors in parallel (`ThreadPoolExecutor`, one task per source; per-company parallelism inside ATS collectors). JobSpy runs as one task internally sequential (rate limits).
- LLM scoring parallel with `max_workers` from config.
- Guard against overlapping runs (CLI + dashboard button): a lock file `data/run.lock` with the PID; if it exists and the PID is alive, exit with a message.

## Scheduling
There is none, on purpose: the owner removed the daily Task Scheduler task because it opened a terminal at every boot. Runs are manual (CLI or dashboard button). Do not add one back unless asked.

## Optional: notify on strong matches
After `save`, if there are new jobs with `score >= 80`, send a summary. Simplest on Windows: `win11toast`/`plyer` desktop notification; or email via SMTP with an app password from `.env`. Keep it a separate `notify` node behind a config flag.
