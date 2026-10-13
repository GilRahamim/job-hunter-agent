---
name: job-storage
description: SQLite storage for the Job Hunter project — the full schema (jobs, runs, source_health, profile), upsert rules that protect user-owned fields like status and notes, cross-board dedupe, run history and application-status tracking. Use this whenever working on jobhunter/db.py, changing what is stored about a job, adding a column, writing migrations, or debugging duplicate jobs or lost statuses.
---

# Storage

Single file `data/jobs.db` via stdlib `sqlite3`. One user, one process at a time (plus the dashboard reading) — no ORM needed.

The full schema is in **`references/schema.sql`**. Execute it on every connect (`CREATE TABLE IF NOT EXISTS`), so a fresh clone just works.

## Ownership of fields — the one rule that matters

| Written by the pipeline | Written only by the user (dashboard) |
|---|---|
| everything about the posting and its scoring | `status`, `notes`, `status_updated` |

`upsert_jobs` uses `INSERT ... ON CONFLICT(id) DO UPDATE SET` and its `SET` list must **not** include user fields. A test must prove that re-collecting and re-scoring a job keeps its status and notes — losing "applied" marks is the worst bug this project can have, because the owner stops trusting the tracker.

## Identity and dedupe
- `id = sha1(url.strip().lower())[:16]` — primary key. Strip tracking params (`utm_*`, `refId`, `trackingId`, `trk`) before hashing; LinkedIn URLs carry them.
- `dedupe_key = normalize(company) + "|" + normalize(title)` where normalize lower-cases, drops `ltd/inc/llc/technologies/group/israel/בע"מ`, and removes non-alphanumerics (keep Hebrew letters).
- During a run: if a job's `id` already exists → only `touch_seen`. If its `dedupe_key` exists under another id (same role on LinkedIn and Greenhouse) → skip it, but prefer keeping the **company-board** version since it has the full description: source priority `greenhouse/lever/ashby/smartrecruiters` > `jobspy:*` > remote boards.

## Helper API (`jobhunter/db.py`)
```python
connect() -> contextmanager[sqlite3.Connection]   # row_factory=Row, applies schema, commits
existing_ids_and_keys() -> tuple[set[str], set[str]]
touch_seen(ids: list[str]) -> None
upsert_jobs(rows: list[dict]) -> None             # rows = Job.to_dict() + scoring fields
jobs_needing_rescore(cv_hash: str, limit: int) -> list[dict]
update_status(job_id: str, status: str, notes: str | None = None) -> None
all_jobs(min_score: float | None = None) -> list[dict]
start_run() -> int;  finish_run(run_id, stats: dict, health: list[dict]) -> None
last_runs(n=20);  health_for_run(run_id)
save_profile(cv_hash, cv_file, data);  load_profile(cv_hash);  latest_profile()
```
- JSON-encode list fields (`matching_skills`, `missing_skills`) with `ensure_ascii=False` so Hebrew stays readable in DB browsers.
- Store timestamps as UTC ISO strings; convert to Israel time (`zoneinfo.ZoneInfo("Asia/Jerusalem")`) only in the dashboard.
- Make the DB path overridable (env `JOBHUNTER_DB` or a function argument) so tests use `tmp_path`.
- Use `PRAGMA journal_mode=WAL` so the dashboard can read while a run writes.

## Statuses
`new → interested → applied → interview → offer`, plus `rejected` and `not_relevant`. Keep the list in one constant (`STATUSES`) used by both the DB layer and the dashboard. `not_relevant` jobs are hidden by default and excluded from re-scoring.

## Schema changes
No migration framework. For a new column: add it to `schema.sql` **and** to a small `_migrate(con)` that runs `ALTER TABLE jobs ADD COLUMN ...` if `PRAGMA table_info(jobs)` lacks it. Never drop the DB to change schema — it holds the owner's application history.
