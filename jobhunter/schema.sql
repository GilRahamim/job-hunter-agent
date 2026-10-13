-- Job Hunter Agent schema. Applied on every connect; safe to re-run.
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,          -- sha1(normalized url)[:16]
    dedupe_key      TEXT,                      -- normalized "company|title"
    source          TEXT,                      -- greenhouse | lever | ashby | smartrecruiters | jobspy:linkedin | remotive ...
    title           TEXT,
    company         TEXT,
    location        TEXT,
    is_remote       INTEGER DEFAULT 0,
    remote_region   TEXT,
    url             TEXT,
    description     TEXT,
    date_posted     TEXT,                      -- ISO date, may be NULL
    first_seen      TEXT,                      -- UTC ISO
    last_seen       TEXT,                      -- UTC ISO, refreshed every run

    -- scoring (pipeline-owned)
    prescore        REAL,
    score           REAL,                      -- LLM score if available, else prescore
    verdict         TEXT,                      -- strong | good | stretch | poor
    seniority_fit   TEXT,
    required_years  REAL,
    matching_skills TEXT,                      -- JSON list
    missing_skills  TEXT,                      -- JSON list
    reasons         TEXT,
    cv_tip          TEXT,
    scored_by       TEXT,                      -- "llm:<model>" | "heuristic"
    scored_at       TEXT,
    cv_hash         TEXT,                      -- CV version used for scoring

    -- user-owned (dashboard only — never written by the pipeline)
    status          TEXT DEFAULT 'new',
    notes           TEXT DEFAULT '',
    status_updated  TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_dedupe ON jobs(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_jobs_score  ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS runs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    started   TEXT,
    finished  TEXT,
    stats     TEXT        -- JSON: collected, new, filtered_by_reason, prescored, llm_scored, errors, duration_s
);

CREATE TABLE IF NOT EXISTS source_health (
    run_id   INTEGER REFERENCES runs(id),
    source   TEXT,
    fetched  INTEGER,
    error    TEXT,
    duration_s REAL
);

CREATE TABLE IF NOT EXISTS tailored_cvs (       -- written by the CV Tailoring Agent
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id             TEXT REFERENCES jobs(id),
    created            TEXT,
    master_hash        TEXT,
    coverage_before    REAL,
    coverage_after     REAL,
    violations_removed INTEGER,
    files              TEXT                       -- JSON list of output paths
);

CREATE TABLE IF NOT EXISTS profile (
    cv_hash  TEXT PRIMARY KEY,
    cv_file  TEXT,
    data     TEXT,        -- CandidateProfile JSON
    created  TEXT
);
