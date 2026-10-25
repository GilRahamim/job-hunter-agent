# Code reading guide: the whole project, in order

How to read the Job Hunter code from the command line to the dashboard. The design and the
reasons behind it are in `docs/ARCHITECTURE.md`; this file only says **what to open, in which
order, and what to look for**. The tool-using agent (`--agent`) has its own guide:
`docs/SMART_AGENT_GUIDE.md`, section 3.

Search for the function name in the file (Ctrl+F / Ctrl+P in the editor).

---

## 1. The map: one search run, from command to dashboard

```
python run_agent.py            (or the "run" button: dashboard.start_run spawns the same command)
        │
        ▼
run_agent.py  main()                                   CLI flags, --user, run lock
   ├─ --agent ─► run_agent_loop() ─► agent_loop/        see SMART_AGENT_GUIDE.md
   └─ else ────► agent.run()                            ① START READING HERE
                     │
                     ▼  LangGraph StateGraph (agent.build_graph), state = PipelineState
   load_profile ─► collect ─► dedupe ─► filter ─► prescore ─┬─► llm_score ─► save ─► notify
        │             │          │         │          │     └─(no LLM / stop)─┘       │
      cv.py      collectors/  dedupe.py filters.py matcher.py   matcher.py   db.py  notify.py
   personalize.py  (parallel)   db.py   details.py  (TF-IDF +    (parallel,  upsert
      llm.py                                         skills)    JobMatch)    finish_run
                                                                                 │
                                                                                 ▼
                                                              data/jobs.db  ◄── dashboard.py
                                                                                 │
                                                       "Prepare with Claude" ─► handoff.py
```

The three scoring stages: **rule filter** (free, removes most jobs) → **pre-score** (free,
ranks them) → **LLM score** (costs time, only the top `matching.llm_top_n`).

---

## 2. Reading order

Read top to bottom. Each step uses only what earlier steps explained.

### 2.1 The foundations (read once, used everywhere)

| # | File : function | What to understand |
|---|---|---|
| 1 | `config.yaml` (skim the section names) | every setting the code reads: `profile`, `filters`, `search`, `sources`, `matching`, `agent`, `notify`, `tailoring`, `llm` |
| 2 | `jobhunter/config.py` `load_config`, `overlay_paths`, `deep_merge` | config.yaml + `JOBHUNTER_CONFIG` overlays + a user's `users/<id>/config.yaml`, merged in that order |
| 3 | `config.py` `active_user`, `user_root`, `data_dir`, `run_dir` | how `JOBHUNTER_USER` moves every path to `users/<id>/` |
| 4 | `jobhunter/models.py` `Job`, `CandidateProfile`, `JobMatch` | the three data shapes. `Job.id` = hash of the cleaned URL; `Job.dedupe_key` = company + title |
| 5 | `jobhunter/llm.py` `get_llm`, `llm_available` | one function returns a LangChain chat model or `None`. `None` = heuristic mode; nothing else breaks |

### 2.2 The pipeline

| # | File : function | What to understand |
|---|---|---|
| 6 | `run_agent.py` `main` | flags → `agent.run(no_llm, sources, limit, rescore, dry_run)` inside `run_lock()` |
| 7 | `jobhunter/agent.py` `PipelineState`, `build_graph`, `run` | the state dict every node reads and returns a part of; the edges; the crash handler that closes the run row |
| 8 | `agent.py` `load_profile_node` → `jobhunter/cv.py` `load_profile` | find the newest CV, read it, LLM or heuristic profile, cached by file hash (`db.save_profile`) |
| 9 | `jobhunter/personalize.py` `personalize` | for `auto_from_cv` users only: queries, role words and the experience limit come from their CV |
| 10 | `agent.py` `collect_node` → `jobhunter/collectors/__init__.py` `_SOURCES`, `collect_all` | the registry (name → module, function, config key) and the parallel run with one health record per source |
| 11 | `jobhunter/collectors/base.py` `CollectorResult`, `get_session`, `clean`, `to_iso` | the collector contract: return jobs + error/warning, **never raise**; one session with timeouts and retry |
| 12 | `collectors/remote_boards.py` (any one `parse_*`) | the simplest collector: JSON in, `list[Job]` out. Read one; the others have the same shape |
| 13 | `collectors/ats.py` `collect_company_boards`, `_one_company`, `fetch_greenhouse` | company boards from `companies.yaml`: one fetch per company, per ATS type |
| 14 | `agent.py` `dedupe_node` → `jobhunter/dedupe.py` `dedupe_batch`, `is_new` | same id → once; same company + title → keep the best source (board > JobSpy > remote) |
| 15 | `agent.py` `filter_node` → `jobhunter/filters.py` `filter_jobs`, `drop_reason` | the rules in order: location, role, seniority, age, experience. Each drop is counted by reason |
| 16 | `filters.py` `junior_reason`, `required_years`, `years_limit` | the experience limit: "3+ years" read from English and Hebrew text |
| 17 | `collectors/details.py` `fill_descriptions` | jobs with no description (LinkedIn, Tech Map) get it fetched, then the experience rules run again |
| 18 | `agent.py` `prescore_node` → `jobhunter/matcher.py` `prescore` | TF-IDF similarity + skill overlap (`skills.py extract_skills`) − years penalty, 0-100, no API cost. Also queues stored jobs for rescoring |
| 19 | `agent.py` `after_prescore` | the conditional edge: LLM step only with a model, jobs, and no stop request (`stop.py`) |
| 20 | `agent.py` `llm_score_node` → `matcher.py` `select_for_llm`, `llm_score`, `build_messages` | top N by pre-score, scored in parallel threads, structured `JobMatch` output, retries |
| 21 | `jobhunter/prompts.py` `SCORE_SYSTEM`, `SCORE_USER`, `PREFERENCES_BLOCK`, `CHOICES_BLOCK` | what the scorer is told. `CHOICES_BLOCK` = the jobs the user marked (`db.status_examples`) |
| 22 | `agent.py` `save_node` → `matcher.py` `scored_row` | one DB row per job; LLM-read years over the limit drop a new job or cap a rescored one; the run stats |
| 23 | `jobhunter/db.py` `upsert_jobs`, `finish_run` + `jobhunter/schema.sql` | only the columns in a row are written; **`status` and `notes` never are** |
| 24 | `agent.py` `notify_node` → `jobhunter/notify.py` | a Windows notification for strong matches |

### 2.3 The dashboard

| # | File : function | What to understand |
|---|---|---|
| 25 | `dashboard.py` `selected_user`, `search_config`, the `USER` / `DB` / `CFG` lines | one process serves every browser tab, so the user and DB path are passed explicitly, never through the env var |
| 26 | `dashboard.py` `main` | the five tabs; an empty DB shows only Profile and Sources |
| 27 | `dashboard.py` `load_jobs`, `sidebar` | DB rows → DataFrame → filtered by the sidebar (score, source, status, location, days) |
| 28 | `dashboard.py` `jobs_tab`, `table_changes`, `set_status` → `db.update_status` | the editable status column: the only place `status` is written |
| 29 | `dashboard.py` `run_controls`, `start_run`, `run_status` → `runlock.py`, `stop.py` | the run button spawns `run_agent.py`; the lock file shows it is running; the stop file asks it to stop |
| 30 | `ui/tokens.py`, `ui/components.py`, `ui/theme.css` | the design system: colors, the Hebrew RTL CSS, KPI cards, chips (see the `dashboard-design` skill) |
| 31 | `dashboard.py` `add_user_form`, `on_add_user` → `jobhunter/users.py` `create_user` | adding a person: `users/<id>/` with their CV and a starter config |

### 2.4 After the search: one application with Claude

| # | File : function | What to understand |
|---|---|---|
| 32 | `dashboard.py` `claude_panel` → `jobhunter/handoff.py` `write_brief`, `build_brief` | one job + the CV + the rules → `data/tailored/<job>/brief.md` |
| 33 | `prompts.py` `HANDOFF_BRIEF` | what Claude is told; the no-invented-facts rule |
| 34 | `handoff.py` `launch_claude`, `subscription_env` | opens Claude Code on the subscription (API keys removed from the child environment) |
| 35 | `handoff.py` `markdown_to_docx` | the CV Claude wrote in Markdown → Word, RTL when Hebrew |

### 2.5 Tests (the fastest way to see a feature work)

| # | File | What to understand |
|---|---|---|
| 36 | `tests/conftest.py` | every test gets a temp users/run folder; nothing touches the real `data/` |
| 37 | `tests/test_pipeline.py` `FakeLLM`, then `test_heuristic_run_saves_filters_and_records_health` | a whole run, offline, from recorded fixtures |
| 38 | `test_pipeline.py` `test_user_status_survives_rerun_and_rescore` | the "never overwrite user fields" rule, proven |
| 39 | `tests/test_filters.py`, `tests/test_matcher.py` | one small test per rule; read the names as a spec |
| 40 | `tests/test_collectors.py` + `tests/fixtures/` | each collector parses a recorded API response |

---

## 3. Where each feature lives

| Feature | Files and functions |
|---|---|
| add a job site | `collectors/<new>.py` `collect_<name>`, `collectors/__init__.py` `_SOURCES`, `config.yaml sources.<key>`, a fixture + test (skill: `job-sources`) |
| add a company | `companies.yaml`; check with `python run_agent.py --check-companies` (`scripts/check_boards.py`) |
| location / role / seniority rules | `filters.py` `location_ok`, `role_fit`, `seniority_ok`; keywords in `config.yaml filters` |
| experience limit | `filters.py` `junior_reason`, `required_years`, `years_limit`, `years_over_limit`, `over_limit_score`; `agent.save_node`; report: `scripts/experience_report.py` |
| pre-score weights | `matcher.py` `prescore`, `W_TFIDF`, `W_SKILLS`; skill names in `skills_vocab.txt` |
| LLM scoring prompt | `prompts.py` `SCORE_SYSTEM` / `SCORE_USER`; built in `matcher.build_messages` |
| learning from the user's choices | `db.status_examples`, `matcher.choices_text`, `prompts.CHOICES_BLOCK`, `config.yaml matching.feedback_examples` |
| rescoring on a CV change | `agent.prescore_node`, `db.jobs_needing_rescore` |
| which model runs | `config.yaml llm`, overlays `config.vllm.yaml` / `config.docker*.yaml`, `llm.get_llm`, `llm.agent_llm_config` |
| several users | `config.py` path helpers, `users.py`, `personalize.py`, `dashboard.selected_user` |
| run lock / stop button | `runlock.py` `run_lock`, `stop.py`, `dashboard.run_controls` |
| application brief for Claude | `handoff.py`, `prompts.HANDOFF_BRIEF`, `dashboard.claude_panel`, skill `apply` |

---

## 4. Words used in the code

| Word | Meaning |
|---|---|
| owner | the user `""`: repo `cv/`, `data/`, `config.yaml`. Others live in `users/<id>/` |
| source / collector | one job site and the function that reads it (`collect_<name>`) |
| health | one record per source per run: jobs fetched, error, warning, seconds (`source_health` table) |
| drop reason | why the rule filter removed a job (`location`, `role`, `senior`, `experience`, `unverified`, `age`, `closed`, `experience_llm`) |
| pre-score | the free 0-100 ranking (`prescore` column) |
| score / `scored_by` | the LLM score and which model gave it; `heuristic` = no LLM, the pre-score is shown |
| rescore | scoring a job already in the DB again (new CV, or `--rescore`) |
| dry run | the whole pipeline, nothing written to the DB |
| brief | the Markdown file the handoff writes for Claude about one job |
