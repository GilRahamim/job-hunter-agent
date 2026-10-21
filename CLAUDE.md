# Job Hunter Agent

A local AI agent that collects software/data/AI job postings (Israel + remote-friendly), scores each one against the owner's CV with an LLM, and shows the results in a Streamlit dashboard where the owner tracks applications.

Owner: Gil — CS graduate (B.Sc., data science track), AI Engineering course graduate, looking for junior–mid development roles of any kind (AI/GenAI, ML, Python/backend, full stack, data science/analysis). Based in Israel. Windows PC.
Other people on the same PC (e.g. a partner, maybe in another field) add themselves in the dashboard by uploading a CV; see "Users" below.

## Read first
- `docs/ARCHITECTURE.md` — components, data flow, schema, design decisions. Treat it as the source of truth; update it when a decision changes.
- `docs/IMPLEMENTATION_PLAN.md` — build order with acceptance criteria per phase. Work one phase at a time and confirm its acceptance check before moving on.

## Skills (in `.claude/skills/`)
Load the matching skill before working on that area — each holds verified API details, prompts, and gotchas that are not obvious from the code.

| Area | Skill |
|---|---|
| Fetching jobs from any site / adding a source or company | `job-sources` |
| Reading the CV and extracting the candidate profile | `cv-profile` |
| Filtering, pre-scoring, LLM scoring, the scoring prompt | `job-matching` |
| LangGraph graph, state, run orchestration, CLI | `agent-pipeline` |
| SQLite schema, upserts, dedupe, status tracking | `job-storage` |
| Streamlit dashboard, Hebrew/RTL UI | `job-dashboard` |
| Tests, fixtures, fake LLM, offline runs | `offline-testing` |
| Tailoring the CV / cover letter for a specific job (2nd agent, planned) | `cv-tailoring` |
| Preparing one application with Claude on the subscription (`/apply <job-id>`) | `apply` |
| Tailoring top matches automatically after a run, headless on the subscription (`claude -p`) | `auto-tailor` |

## Stack
Python 3.11+, LangGraph, LangChain (`init_chat_model` for provider-agnostic LLM), Pydantic v2, SQLite (stdlib `sqlite3`), scikit-learn (TF-IDF), python-jobspy, requests, Streamlit, pypdf, python-docx, PyYAML, python-dotenv, pytest.

## Layout
```
config.yaml          user-editable settings (queries, filters, LLM)
companies.yaml       company career boards (Greenhouse/Lever/Ashby/SmartRecruiters slugs)
.env                 API keys (never commit)
cv/                  the owner's CV (newest file wins)
data/jobs.db         the owner's SQLite DB (gitignored); data/tailored/<job>/ = Claude briefs + outputs
users/<id>/          another person: cv/, data/, config.yaml overlay (gitignored)
jobhunter/
  config.py models.py db.py llm.py cv.py filters.py matcher.py prompts.py agent.py
  dedupe.py runlock.py stop.py notify.py skills.py
  users.py personalize.py      people added from the dashboard; settings derived from their CV
  handoff.py                   one job -> brief for Claude Code / claude.ai (subscription), md -> docx
  collectors/  base.py  ats.py  jobspy_source.py  remote_boards.py  serpapi.py  techmap.py  getro.py
               details.py (missing descriptions)  __init__.py (registry)
  agent_loop/  graph.py  tools.py  memory.py   (tool-using agent, --agent; memory = past queries)
  tailor/      (empty: CV Tailoring Agent, Phase 8, planned)
run_agent.py         CLI entry point (search agent)
dashboard.py         Streamlit app;  ui/  design system (tokens, CSS, components)
scripts/             check_boards.py, sync_companies.py (add boards from Israeli Tech Map + VC boards),
                     experience_report.py (stored jobs over the experience limit, and how they got in),
                     agent_report.py (agent picks vs what the owner pursued / dismissed: precision)
tests/               pytest + fixtures/ (recorded API responses)
docs/                ARCHITECTURE.md, IMPLEMENTATION_PLAN.md, USER_GUIDE.he.md (for people who just use it)
```

## Commands
```bash
pip install -r requirements-dev.txt # app + tests (requirements.txt = app only)
python run_agent.py                 # full run: collect → filter → score → save
python run_agent.py --no-llm        # heuristic scoring only (free)
python run_agent.py --sources ats,remotive --limit 50   # partial run while developing
python run_agent.py --check-companies                   # validate companies.yaml
python run_agent.py --agent --goal 5 --dry-run          # tool-using agent loop (jobhunter/agent_loop/)
python run_agent.py --user dana                         # run for a person added in the dashboard
python -m jobhunter.handoff --list | <job_id> [--launch] # brief for Claude (subscription)
streamlit run dashboard.py
pytest -q                           # also runs in CI on every push: .github/workflows/tests.yml
```

## Conventions
- Every collector returns `list[Job]` and never raises: catch errors, log them, and report them in the source-health record. One broken site must not stop a run.
- Network code goes through one `requests.Session` with a User-Agent, timeouts (15s), and retry with backoff on 429/5xx.
- Config values come from `config.yaml`; do not hard-code queries, keywords, thresholds, or model names in code.
- The LLM is optional. With `provider: none` or no API key, everything still works using heuristic scores.
- Never overwrite user-owned fields (`status`, `notes`) when re-collecting or re-scoring.
- Keep all LLM prompts in `jobhunter/prompts.py` so they can be tuned in one place.
- User-facing dashboard text is Hebrew; code, comments, logs, and docs are English.
- Type hints everywhere; small functions; no class hierarchies where a function will do.
- Before claiming a phase is done, run its acceptance check from the implementation plan and show the output.

- The tailoring agent never adds facts that are not in `cv/cv_master.yaml` — see `cv-tailoring`. The Claude handoff brief carries the same rule.
- The owner's personal CV rules and confirmed facts: `cv-tailoring/references/owner-cv-rules.md` (rules, committed) and `cv/notes/` (facts, gitignored — never copy them into committed files).

## Users
- The owner is user `""`: repo `cv/`, `data/`, `config.yaml`. Others live in `users/<id>/`; their `config.yaml` is merged over the main one.
- CLI processes follow `JOBHUNTER_USER` (`--user`); path helpers (`config.run_dir`, `db.db_path`, `stop.*`) resolve from it. The dashboard serves every browser session from one process, so it must pass the user / DB path explicitly and never set the env var.
- `auto_from_cv: true` users get queries, role filter and experience limit from their CV (`personalize.py`); keep the owner's hand-tuned `config.yaml` values out of their way. The agent loop is owner-only.
- Tests: `conftest.py` points `JOBHUNTER_USERS_DIR` / `JOBHUNTER_RUN_DIR` at temp folders; never write under the repo's `users/` or `data/` from a test.

## Things to avoid
- Scraping LinkedIn directly with custom code — use JobSpy, which is already maintained against it. LinkedIn rate-limits aggressively; keep `results_per_query` modest and do not loop.
- Sending every collected job to the LLM — pre-filter and pre-score first (cost and time).
- Storing API keys anywhere except `.env`.
