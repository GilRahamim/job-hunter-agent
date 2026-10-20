# Implementation Plan

Build in this order. Each phase ends with an **acceptance check** — run it and show the output before starting the next phase. Each phase lists the skill(s) to load and a prompt the owner can paste into Claude Code.

---

## Phase 0 — Project skeleton
**Skills:** none (read `CLAUDE.md`, `docs/ARCHITECTURE.md`)

Tasks
- Create the package layout from `CLAUDE.md`, `requirements.txt`, `.gitignore` (`.env`, `data/`, `cv/*` except `cv/README.md`, `__pycache__`), `.env.example`.
- `jobhunter/config.py`: load `config.yaml`, `companies.yaml`, `.env` (cached).
- `jobhunter/models.py`: `Job`, `CandidateProfile`, `JobMatch` exactly as in the architecture doc.
- `git init` and first commit.

Acceptance: `python -c "from jobhunter.config import load_config; print(load_config()['llm'])"` prints the LLM block; `pytest -q` runs (zero tests is fine).

> Prompt: *Read CLAUDE.md and docs/ARCHITECTURE.md, then do Phase 0 of docs/IMPLEMENTATION_PLAN.md.*

---

## Phase 1 — Storage
**Skills:** `job-storage`

Tasks: `jobhunter/db.py` with the schema, `upsert_jobs`, `existing_ids_and_keys`, `touch_seen`, `update_status`, run/health/profile helpers. Tests in `tests/test_db.py` using a temp DB path.

Acceptance: tests prove that re-upserting a job with a new score keeps its `status` and `notes`.

> Prompt: *Use the job-storage skill and do Phase 1.*

---

## Phase 2 — Collectors
**Skills:** `job-sources`, `offline-testing`

Tasks
1. `collectors/base.py`: shared session, retry, `html_to_text`, `CollectorResult(jobs, error)`.
2. `collectors/ats.py`: Greenhouse, Lever, Ashby, SmartRecruiters — driven by `companies.yaml`, run companies in a thread pool.
3. `collectors/remote_boards.py`: Remotive, RemoteOK, Himalayas, WeWorkRemotely (RSS), Arbeitnow.
4. `collectors/jobspy_source.py`: LinkedIn, Indeed (`country_indeed="israel"`), Glassdoor, Google.
5. `collectors/serpapi.py` (optional, skipped without key).
6. `collectors/__init__.py`: registry `{name: fn}` + `collect_all(config, only=None)` running sources in parallel.
7. Record one fixture per source in `tests/fixtures/` and write parser tests against them.
8. `scripts/check_boards.py` (copy from the skill) wired to `run_agent.py --check-companies`.

Acceptance: `python -m jobhunter.collectors --source ats --limit 5` prints jobs from at least 5 companies with non-empty descriptions; parser tests pass offline.

> Prompt: *Use the job-sources and offline-testing skills and do Phase 2. Start with the ATS collectors, show me sample output, then continue.*

---

## Phase 3 — CV profile
**Skills:** `cv-profile`

Tasks: `jobhunter/llm.py` (`get_llm()`), `jobhunter/prompts.py` (profile prompt), `jobhunter/cv.py` (find newest CV, extract text, hash, LLM extraction with heuristic fallback, cache in DB).

Acceptance: with the real CV in `cv/`, `python -m jobhunter.cv` prints the profile JSON; a second run is instant (cache hit); `--no-llm` produces a heuristic profile.

> Prompt: *Use the cv-profile skill and do Phase 3. My CV is in cv/.*

---

## Phase 4 — Filtering and matching
**Skills:** `job-matching`, `offline-testing`

Tasks: `filters.py`, `matcher.py` (prescore + parallel LLM scoring with retries), scoring prompt in `prompts.py`, skills vocabulary file `jobhunter/skills_vocab.txt`.

Acceptance: unit tests for filters (Israel city in Hebrew, "Remote – US only" rejected, "Senior" dropped when enabled); on 20 real jobs the LLM returns valid `JobMatch` objects, and a manual look at the top 5 makes sense.

> Prompt: *Use the job-matching skill and do Phase 4. Show me the top 10 scored jobs with reasons when done.*

---

## Phase 5 — Agent pipeline + CLI
**Skills:** `agent-pipeline`

Tasks: `agent.py` LangGraph graph, `run_agent.py` with flags (`--no-llm`, `--sources`, `--limit`, `--rescore`, `--check-companies`, `--dry-run`), logging to `data/logs/`.

Acceptance: `python run_agent.py` completes end to end, writes a `runs` row with stats and per-source health; a second run immediately after scores ~0 new jobs.

> Prompt: *Use the agent-pipeline skill and do Phase 5, then run it once for real.*

---

## Phase 6 — Dashboard
**Skills:** `job-dashboard`

Tasks: `dashboard.py` with the tabs from the architecture doc, RTL CSS, status editing, run button, insights.

Acceptance: `streamlit run dashboard.py` shows real data; changing a job's status persists after refresh; the run button starts a run and the sources tab shows its health.

> Prompt: *Use the job-dashboard skill and do Phase 6. Use the frontend-design skill for the visual polish.*

---

## Phase 7 — Scheduling and polish
**Skills:** `agent-pipeline`

Tasks: README in Hebrew, optional desktop notification / email digest of new strong matches.

Acceptance: a manual run produces a new run row. (A daily Task Scheduler task was built here and later removed: runs are manual.)

---

## Phase 8 — CV Tailoring Agent (not started)
**Skills:** `cv-tailoring`, `offline-testing`, `job-dashboard`

Meanwhile the **Claude handoff** (built; `jobhunter/handoff.py`, ARCHITECTURE §15) does this job on the owner's Claude subscription: the dashboard writes a brief per job and opens Claude Code on it. Build Phase 8 when tailoring has to run unattended (e.g. `tailoring.auto_min_score`) or needs the mechanical verify loop; it can reuse the brief's content and the handoff's output folder.

Tasks
1. Master CV: generate a draft `cv/cv_master.yaml` from the CV (MASTER_DRAFT prompt). **Stop here — the owner reviews and enriches it** (more bullets per project, real skill levels).
2. `jobhunter/tailor/`: models (`JobRequirements`, `TailoredCV`, `BulletCheck`), nodes, graph with the verify → rewrite loop, `tailored_cvs` table.
3. `cv/template.docx` with docxtpl tags + `render.py`; `tailor_cv.py` CLI.
4. Fabrication test: fake LLM injects an invented skill → output must not contain it.
5. Dashboard: "התאם קו"ח למשרה" button in the job panel, download buttons, coverage before/after, `changes.md`.
6. Optional: `tailoring.auto_min_score` hook after the search pipeline.

Acceptance: `python tailor_cv.py --job <id>` on 3 real top jobs produces DOCX files that open in Word; every bullet traces to master `source_ids`; the fabrication test passes; the owner reads the 3 CVs and confirms nothing is untrue.

> Prompt: *Use the cv-tailoring skill and do Phase 8, step 1 only. Then wait for me to edit cv_master.yaml.*

---

## Built after Phase 7
- Tool-using agent loop (`--agent`), stop button, junior-only mode, Israeli Tech Map / Getro sources.
- Several users on one PC, each starting from an uploaded CV (`users.py`, `personalize.py`).
- Claude handoff: one job → brief → Claude Code or claude.ai on the subscription (`handoff.py`, `/apply`).
- Scoring learns from the user's statuses (`matching.feedback_examples`).
- CI: `.github/workflows/tests.yml` runs `pytest -q` on every push and pull request (Ubuntu 3.11 / 3.13, Windows 3.13).

## Later ideas (ranked: value for the effort)
1. **Multilingual embedding pre-score** behind the same `prescore()` interface. TF-IDF with English stop words is weak on Hebrew postings and on CVs outside tech, which matters now that other people use the tool. A small multilingual sentence-transformers model runs locally on CPU.
2. **Agent loop for every user**: move the CS-junior paragraph of `AGENT_SYSTEM` behind a config switch (one focus text for the owner, one built from the profile), then drop the `auto_from_cv` refusal in `agent_loop.run`.
3. **Unattended tailoring for top matches**: after a run, write briefs for new jobs above `tailoring.auto_min_score` (the handoff already does the writing part); either Phase 8 through the API, or `claude -p` on the subscription, within its usage limits.
4. **Split `dashboard.py`** (now ~830 lines) into tab modules (`ui/tabs/jobs.py`, `profile.py`, …), keeping `dashboard.py` as the entry point; update the two tests that read its source.
5. **Follow-up reminders**: the pipeline tab already flags applications older than 10 days; add them to the Windows notification and a weekly digest.
6. **Weekly gap report**: most requested skills you lack, with the trend over time (the data is already in `missing_skills`).
7. **Company research tool** for the agent loop: read the company's About/careers page before scoring (size, product, stack).
8. Direct collectors for AllJobs / Drushim.
