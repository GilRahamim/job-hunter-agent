"""SQLite storage. Pipeline-owned and user-owned fields are strictly separated."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from jobhunter.config import ROOT

STATUSES = ["new", "interested", "applied", "interview", "offer", "rejected", "not_relevant"]
_HIDDEN_STATUSES = ("rejected", "not_relevant")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

# Columns the pipeline may write. status / notes / status_updated are deliberately absent.
PIPELINE_COLUMNS = [
    "dedupe_key", "source", "title", "company", "location", "is_remote", "remote_region",
    "url", "description", "date_posted",
    "prescore", "score", "verdict", "seniority_fit", "required_years",
    "matching_skills", "missing_skills", "reasons", "cv_tip",
    "scored_by", "scored_at", "cv_hash",
]
_JSON_COLUMNS = ("matching_skills", "missing_skills")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def db_path(path: str | Path | None = None) -> Path:
    return Path(path or os.environ.get("JOBHUNTER_DB") or ROOT / "data" / "jobs.db")


def source_priority(source: str) -> int:
    """Lower is better: company boards (full descriptions) beat JobSpy beat remote boards."""
    if source in ("greenhouse", "lever", "ashby", "smartrecruiters", "workday", "comeet"):
        return 0
    if source.startswith("jobspy"):
        return 1
    return 2


def _migrate(con: sqlite3.Connection) -> None:
    """Add columns introduced after a DB was created. Never drop the DB."""
    # Example:  _add_column(con, "jobs", "new_col", "TEXT")


def _add_column(con: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    cols = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


@contextmanager
def connect(path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    p = db_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _migrate(con)
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _decode(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for col in _JSON_COLUMNS:
        if d.get(col):
            d[col] = json.loads(d[col])
    return d


# ---------------------------------------------------------------- jobs

def existing_ids_and_keys(path: str | Path | None = None) -> tuple[set[str], set[str]]:
    with connect(path) as con:
        rows = con.execute("SELECT id, dedupe_key FROM jobs").fetchall()
    return {r["id"] for r in rows}, {r["dedupe_key"] for r in rows if r["dedupe_key"]}


def touch_seen(ids: list[str], path: str | Path | None = None) -> None:
    if not ids:
        return
    with connect(path) as con:
        con.executemany("UPDATE jobs SET last_seen = ? WHERE id = ?", [(now_utc(), i) for i in ids])


def upsert_jobs(rows: list[dict[str, Any]], path: str | Path | None = None) -> None:
    """Insert or update postings. Only columns present in a row are updated, so a
    collection-only row never wipes scores and a scoring row never wipes the posting.
    status / notes / status_updated are never written here."""
    now = now_utc()
    with connect(path) as con:
        for row in rows:
            cols = [c for c in PIPELINE_COLUMNS if c in row]
            values = [_dumps(row[c]) if c in _JSON_COLUMNS and row[c] is not None else row[c]
                      for c in cols]
            insert_cols = ["id", *cols, "first_seen", "last_seen"]
            sets = ", ".join([f"{c} = excluded.{c}" for c in cols] + ["last_seen = excluded.last_seen"])
            con.execute(
                f"INSERT INTO jobs ({', '.join(insert_cols)}) "
                f"VALUES ({', '.join('?' * len(insert_cols))}) "
                f"ON CONFLICT(id) DO UPDATE SET {sets}",
                [row["id"], *values, now, now],
            )


def jobs_needing_rescore(cv_hash: str, limit: int | None, path: str | Path | None = None, *,
                         force: bool = False, include_heuristic: bool = False,
                         min_prescore: float = 0) -> list[dict]:
    """Jobs to score again, best pre-score first, excluding rejected / not_relevant.

    Default: scored with a different CV version. `force`: every job. `include_heuristic`:
    also jobs that only have a heuristic score (use when an LLM is available now).
    `limit=None`: no cap (the caller filters the rows first, then caps)."""
    marks = ",".join("?" * len(_HIDDEN_STATUSES))
    heuristic = " OR scored_by = 'heuristic'" if include_heuristic else ""
    stale = "1" if force else f"(cv_hash IS NULL OR cv_hash != ?{heuristic})"
    params: list[Any] = [] if force else [cv_hash]
    with connect(path) as con:
        rows = con.execute(
            f"SELECT * FROM jobs WHERE {stale} AND status NOT IN ({marks}) "
            f"AND COALESCE(prescore, 0) >= ? ORDER BY prescore DESC LIMIT ?",
            [*params, *_HIDDEN_STATUSES, min_prescore, -1 if limit is None else limit],
        ).fetchall()
    return [_decode(r) for r in rows]


def update_status(job_id: str, status: str, notes: str | None = None,
                  path: str | Path | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    with connect(path) as con:
        if notes is None:
            con.execute("UPDATE jobs SET status = ?, status_updated = ? WHERE id = ?",
                        (status, now_utc(), job_id))
        else:
            con.execute("UPDATE jobs SET status = ?, notes = ?, status_updated = ? WHERE id = ?",
                        (status, notes, now_utc(), job_id))


def all_jobs(min_score: float | None = None, path: str | Path | None = None) -> list[dict]:
    with connect(path) as con:
        if min_score is None:
            rows = con.execute("SELECT * FROM jobs ORDER BY score DESC").fetchall()
        else:
            rows = con.execute("SELECT * FROM jobs WHERE score >= ? ORDER BY score DESC",
                               (min_score,)).fetchall()
    return [_decode(r) for r in rows]


# ---------------------------------------------------------------- runs

def start_run(path: str | Path | None = None) -> int:
    with connect(path) as con:
        return con.execute("INSERT INTO runs (started) VALUES (?)", (now_utc(),)).lastrowid


def finish_run(run_id: int, stats: dict, health: list[dict], path: str | Path | None = None) -> None:
    with connect(path) as con:
        con.execute("UPDATE runs SET finished = ?, stats = ? WHERE id = ?",
                    (now_utc(), _dumps(stats), run_id))
        con.executemany(
            "INSERT INTO source_health (run_id, source, fetched, error, duration_s) VALUES (?,?,?,?,?)",
            [(run_id, h["source"], h.get("fetched", 0), h.get("error"), h.get("duration_s"))
             for h in health],
        )


def last_runs(n: int = 20, path: str | Path | None = None) -> list[dict]:
    with connect(path) as con:
        rows = con.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["stats"] = json.loads(d["stats"]) if d["stats"] else {}
        out.append(d)
    return out


def health_for_run(run_id: int, path: str | Path | None = None) -> list[dict]:
    with connect(path) as con:
        rows = con.execute("SELECT * FROM source_health WHERE run_id = ?", (run_id,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- profile

def save_profile(cv_hash: str, cv_file: str, data: dict, path: str | Path | None = None) -> None:
    with connect(path) as con:
        con.execute(
            "INSERT INTO profile (cv_hash, cv_file, data, created) VALUES (?,?,?,?) "
            "ON CONFLICT(cv_hash) DO UPDATE SET cv_file = excluded.cv_file, data = excluded.data",
            (cv_hash, cv_file, _dumps(data), now_utc()),
        )


def load_profile(cv_hash: str, path: str | Path | None = None) -> dict | None:
    with connect(path) as con:
        row = con.execute("SELECT data FROM profile WHERE cv_hash = ?", (cv_hash,)).fetchone()
    return json.loads(row["data"]) if row else None


def latest_profile(path: str | Path | None = None) -> dict | None:
    with connect(path) as con:
        row = con.execute("SELECT cv_hash, cv_file, data FROM profile ORDER BY created DESC LIMIT 1").fetchone()
    if not row:
        return None
    return {"cv_hash": row["cv_hash"], "cv_file": row["cv_file"], "data": json.loads(row["data"])}


# ---------------------------------------------------------------- dashboard helpers

_TABLE_COLUMNS = ("id, source, title, company, location, is_remote, remote_region, url, date_posted, "
                  "first_seen, last_seen, prescore, score, verdict, seniority_fit, required_years, matching_skills, "
                  "missing_skills, scored_by, status, notes, status_updated")


def jobs_table(path: str | Path | None = None) -> list[dict]:
    """All jobs without the heavy description column (the dashboard table frame)."""
    with connect(path) as con:
        rows = con.execute(f"SELECT {_TABLE_COLUMNS} FROM jobs").fetchall()
    return [_decode(r) for r in rows]


def not_junior_ids(cfg: dict[str, Any], path: str | Path | None = None) -> set[str]:
    """Ids of stored jobs that fail the junior check (senior title, required experience,
    unverifiable) under the current config, including jobs saved before the check existed."""
    from jobhunter.filters import junior_reason
    from jobhunter.models import Job

    with connect(path) as con:
        rows = con.execute("SELECT id, title, description FROM jobs").fetchall()
    return {r["id"] for r in rows
            if junior_reason(Job("", r["title"] or "", "", "", description=r["description"] or ""), cfg)}


def job_detail(job_id: str, path: str | Path | None = None) -> dict | None:
    with connect(path) as con:
        row = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _decode(row) if row else None


def update_notes(job_id: str, notes: str, path: str | Path | None = None) -> None:
    with connect(path) as con:
        con.execute("UPDATE jobs SET notes = ? WHERE id = ?", (notes, job_id))


def health_history(n_runs: int = 14, path: str | Path | None = None) -> list[dict]:
    """Fetched counts per source for the last n runs."""
    with connect(path) as con:
        rows = con.execute(
            "SELECT h.run_id, r.started, h.source, h.fetched, h.error FROM source_health h "
            "JOIN runs r ON r.id = h.run_id WHERE h.run_id IN "
            "(SELECT id FROM runs ORDER BY id DESC LIMIT ?) ORDER BY h.run_id", (n_runs,)).fetchall()
    return [dict(r) for r in rows]


def backfill_required_years(path: str | Path | None = None) -> int:
    """Fill required_years (from the stored description) for jobs scored before it was recorded."""
    from jobhunter.filters import required_years

    with connect(path) as con:
        rows = con.execute("SELECT id, title, description FROM jobs WHERE required_years IS NULL").fetchall()
        con.executemany("UPDATE jobs SET required_years = ? WHERE id = ?",
                        [(required_years(f"{r['title']}\n{r['description'] or ''}"), r["id"]) for r in rows])
    return len(rows)
