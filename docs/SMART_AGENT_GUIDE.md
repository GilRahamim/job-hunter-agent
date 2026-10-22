# Smart agent guide: what changed, commands, where to read the code

The search agent (`python run_agent.py --agent`, code in `jobhunter/agent_loop/`) was reworked in
PR #6 (https://github.com/GilRahamim/job-hunter-agent/pull/6, merged 2026-10-21) and a follow-up fix:

| Commit | What |
|---|---|
| `a0d6cfc` | #1 duplicates, #2 batching / free searches, #4 memory |
| `eff5177` | #3 scorer, #6 smaller context |
| `d99f222` | #5 precision report, #7 dry groups / exact DONE |
| `1f86c9e` | follow-up: billing / API-key errors stop scoring, no re-saves, LinkedIn 429 handling |

See also: `docs/ARCHITECTURE.md` (design, the source of truth) and `CLAUDE.md` (all commands).

---

## 1. What changed

There is still **one agent** (the search agent in `jobhunter/agent_loop/`). No new libraries, no new
external APIs, no database schema change.

| # | Change | Why | Main code |
|---|---|---|---|
| 1 | **Duplicate fix**: the same role found on two sources in one run (LinkedIn + company page) is kept once | it was read, saved and stored twice | `tools._add_candidate` |
| 2 | **More matches per step budget**: read 2-4 postings in one turn, save next turn; a save in the same turn as its read is refused; searches on an already-loaded board list are free | 50 steps were too few for 10 matches + 11 groups | `prompts.AGENT_SYSTEM`, `tools.is_free`, `tools.save_match`, `graph.compact_history` |
| 3 | **The agent picks, the regular scorer scores**: `save_match(job_id, reason)` no longer takes a score; the regular search's scoring prompt scores the job right away | one score scale for agent + regular jobs; full details (skills, CV tip) in the dashboard | `tools.score_job`, `graph.scorer_config`, `matcher.llm_score` |
| 4 | **Memory between runs**: each run stores per-query results; the next run is told which queries worked | the agent started from zero every run | `memory.py` (new) |
| 5 | **Precision report**: agent picks vs what you did with them in the dashboard | to measure whether changes really help | `scripts/agent_report.py` (new) |
| 6 | **Smaller context**: old search results lose rows of jobs already read and stale notes; old replies lose `<think>` blocks and are cut to 300 chars | small local model, long runs | `graph.trim_search`, `graph.trim_reply` |
| 7 | **Dry role groups** (no strong match in recent runs) get one search per run; the run ends early only on an exact `DONE` reply | budget goes to groups that produce matches | `memory.group_history`, `tools.group_cap`, `graph.said_done` |
| fix | **Robustness** (`1f86c9e`): a billing / API-key error stops scoring for the rest of the run (no useless retries) and tells the agent to wrap up; saving a job twice changes nothing (no re-scoring), except one retry when its scorer failed; a LinkedIn 429 drops LinkedIn for the rest of the run (`linkedin` searches cover Indeed only) | real-run problems | `matcher.fatal_llm_error`, `tools.score_job` (`scorer_down`), `tools.save_match`, `tools.jobspy_sites` |

Precision in the report:

$$\text{precision} = \frac{\text{pursued}}{\text{pursued} + \text{dismissed}}$$

pursued = interested / applied / interview / offer / rejected (you applied, they said no);
dismissed = not relevant.

### New settings in `config.yaml` (under `agent:`)

| Setting | Default | Meaning |
|---|---|---|
| `scorer` | `main` | who scores saved jobs: `main` = the `llm:` section (Claude Haiku now: same scale as the regular search, one paid call per saved job); `agent` = the agent's own local model (free, different scale). `main` falls back to the agent's model if `llm` is off |
| `memory_runs` | `5` | how many past agent runs the memory looks at; `0` = off |
| `dry_group_searches` | `3` | a group searched this many times in those runs without one strong match is DRY (1 search per run); `0` = off |

### What a run now stores (`runs.stats` JSON, no schema change)
`queries` (per search: query, source, found, new, read, saved, strong), `scorer` (model name),
`charged_searches` (searches counted against `max_searches`; `searches` = all of them).

### Tests
PR #6 added 21 tests (`tests/test_agent_loop.py`, `tests/test_db.py`); the follow-up fix added more
(`tests/test_agent_loop.py`, `tests/test_matcher.py`). Run `pytest -q`.

---

## 2. Commands

The owner's PC is Windows. The commands below work in **PowerShell** unless marked otherwise.

### 2.1 Git: test a branch before it goes into `master`

`master` is the official version; a branch (e.g. `claude/...`) is a separate line of work that
changes nothing in `master` until it is merged. `origin` is Git's name for the copy on GitHub.
Replace `<branch>` with the branch name.

| Step | Command | What it does |
|---|---|---|
| 1 | `git fetch origin` | download the latest branches from GitHub (`origin`) into local snapshots (`origin/...`). Changes none of your files |
| 2 | `git checkout <branch>` | switch your folder to the branch (creates the local branch from `origin/<branch>` the first time) |
| 3 | `git branch --show-current` | print the branch you are on |
| 4 | `git log --oneline -4` | last 4 commits, one line each (`--oneline` = short id + title; `-4` = how many) |
| 5 | `git status` | changed / uncommitted files; also says if the branch matches GitHub |
| 6 | `git pull` | (on the branch) get commits pushed to it since |
| 7 | `git diff master...<branch> --stat` | which files the branch changes (`...` = since the branch left master; `--stat` = file list + line counts, drop it to see the full diff) |
| approve | merge on GitHub: PR page, **Merge pull request** (or locally: `git checkout master`, `git merge <branch>`, `git push origin master`) | puts the branch into `master` |
| then | `git checkout master` | back to the official version |
| then | `git pull origin master` | bring the merged changes into your local `master` |
| then | `git branch -d <branch>` | delete the local branch (`-d` refuses if it was not merged: safe) |

### 2.2 Setup and tests

| Command | Flags |
|---|---|
| `pip install -r requirements-dev.txt` | `-r <file>` = install every package listed in the file (app + test tools) |
| `pytest -q` | `-q` = quiet: one dot per test + summary. Everything should pass |
| `pytest -q tests/test_agent_loop.py` | only the agent-loop tests (a file path limits pytest to that file) |
| `pytest -q -k dry_groups` | `-k <text>` = only tests whose name contains the text |
| `pytest -q -x` | `-x` = stop at the first failure |

### 2.3 Back up the database before a real ("wet") run

A run without `--dry-run` writes to `data/jobs.db`. Git does not track it, so switching branches will not undo it.

| Shell | Back up | Restore |
|---|---|---|
| PowerShell | `Copy-Item data\jobs.db data\jobs.backup.db` | `Copy-Item data\jobs.backup.db data\jobs.db -Force` |
| cmd | `copy data\jobs.db data\jobs.backup.db` | `copy /Y data\jobs.backup.db data\jobs.db` |

`-Force` / `/Y` = overwrite without asking. Stop the dashboard before restoring (Ctrl+C in its terminal;
closing the browser tab is not enough): a status change or a "run now" during the copy would be lost or
break the restored file.

### 2.4 Running the agent

| Command | Flags |
|---|---|
| `python run_agent.py --agent --goal 5 --dry-run` | `--agent` = the tool-using agent (not the fixed pipeline). `--goal 5` = stop after 5 saved jobs scoring >= `agent.min_match_score` (70); default `agent.goal_matches` (10). `--dry-run` = no jobs and no run record written, so it does **not** feed the memory. It is **not free**: with `agent.scorer: main` every save is still one paid scorer call. It can still touch `data/jobs.db`: a changed CV writes its new profile there |
| `python run_agent.py --agent --goal 5` | the real run: saves jobs and the run's per-query results (feeds memory #4 and dry groups #7) |
| `python run_agent.py --agent --goal 5 --max-steps 30` | `--max-steps N` = model turns before a hard stop; default `agent.max_steps` (50) |
| `python run_agent.py` | the regular fixed pipeline (unchanged by these changes) |
| `python run_agent.py --no-llm` | pipeline with keyword scores only, no LLM (free) |
| `python run_agent.py --sources ats,remotive --limit 50` | pipeline on some sources only (`--sources` comma list), `--limit 50` = at most 50 jobs per source, and per company board for `ats` (so `ats` can still bring thousands) |
| `python run_agent.py --rescore` | pipeline: re-score stored jobs against the current CV |
| `python run_agent.py --check-companies` | validate `companies.yaml` and exit |
| `python run_agent.py --user dana` | run for a person added in the dashboard. **Not with `--agent`**: the agent is owner-only |
| `streamlit run dashboard.py` | the dashboard (also has the "smart agent" toggle) |

What to look for in the agent's log. The console shows INFO lines; the file `data/logs/run-*.log`
also has DEBUG lines, where tool results are logged cut to 200 characters (`tool <name> -> ...`).

| Log line | Where | Meaning |
|---|---|---|
| `agent: <model>, scorer: <model> \| goal ...` | console | which model searches and which model scores (#3) |
| several `step N: read_posting(...)` with the **same N** | console | the model batches (#2). One per step = it does not; still works, just slower |
| `agent: scorer unavailable for the rest of this run: ...` | console | billing / API-key error: saves after it are unscored (follow-up fix) |
| `agent stopped (goal_reached / step_limit / model_stopped ...)` | console | why the run ended |
| `tool save_match -> Saved ... Scorer: 72 (good) ...` | log file | the scorer's verdict (#3) |
| `tool search_jobs -> LinkedIn is rate-limited for the rest of this run ...` | log file | LinkedIn answered 429; `linkedin` searches now cover Indeed only (follow-up fix) |

Memory (#4) and dry groups (#7) go only into the model's first message, not into the log. To see them
work: the run summary's `saved matches` and the dashboard after a few real runs, or
`python scripts/agent_report.py`.

### 2.5 Reports

| Command | Flags |
|---|---|
| `python scripts/agent_report.py` | precision of agent picks vs regular search, by score band and role group (#5) |
| `python scripts/agent_report.py --since 2026-10-22` | `--since YYYY-MM-DD` = only jobs first seen on/after that date (compare before / after a change). Dates are UTC (Israel is UTC+2/+3): for a run after midnight local time, give the day before |
| `python scripts/experience_report.py` | existing: stored jobs over the experience limit and how they got in. `--user <id>` for another person |

### 2.6 Checking an agent change

1. Back up `data/jobs.db` (2.3).
2. `git fetch origin` then `git checkout <branch>` (2.1).
3. `pytest -q`.
4. Check `agent.scorer` in `config.yaml` (`main` = the `llm:` model, paid per saved job, also in a dry run;
   `agent` = the local model, free).
5. Dry run: `python run_agent.py --agent --goal 5 --dry-run`, check the log (2.4).
6. Real run: `python run_agent.py --agent --goal 5`, check the jobs in the dashboard.
7. 2-3 more real runs over a few days: memory and dry groups shape the searches (2.4).
8. Mark jobs in the dashboard, then `python scripts/agent_report.py --since <the day before step 6>`
   (UTC dates, 2.5).
9. Good: merge into `master` (2.1). Problem: fix on the same branch, then `git pull` there.

---

## 3. Reading the code

### 3.1 The map: one agent run, from command to database

```
python run_agent.py --agent
        │
        ▼
run_agent.py  main() ─► run_agent_loop()                       CLI, run lock, prints the summary
        │
        ▼
agent_loop/graph.py  run()                                     ① START READING HERE
   ├─ load config, pick agent model + scorer (scorer_config)
   ├─ load CV profile, known jobs from the DB
   ├─ memory.py: memory_text(), group_history(), dry_groups()  ← past runs (#4, #7)
   ├─ initial_messages()  ─► prompts.py AGENT_SYSTEM / AGENT_START (+ AGENT_MEMORY)
   │
   ├─ build_graph()  ── the LangGraph loop ────────────────────────────────────┐
   │      agent_node:  model.invoke(compact_history(messages))    (#6 trims)  │
   │           │ tool calls?                                                  │
   │           ├─ yes ─► tools_node ─► tools.py:                              │
   │           │            get_profile / search_jobs / read_posting /        │
   │           │            save_match ─► score_job ─► matcher.llm_score (#3) │
   │           │         after_tools: goal reached? step limit? ─► back ──────┤
   │           └─ no  ─► said_done? (#7) ─► nudge once ─► back                │
   │                          └─► stop                                        │
   └──────────────────────────────────────────────────────────────────────────┘
   ├─ result_rows()  ─► db.upsert_jobs()                       jobs to the DB
   └─ stats incl. queries (memory.query_stats) ─► db.finish_run()   feeds the next run's memory
```

### 3.2 Reading order

Read top to bottom. Each step uses only what earlier steps explained.

Search for the function name in the file (Ctrl+F / Ctrl+P in the editor).

| # | File : function | Read | What to understand |
|---|---|---|---|
| 1 | `docs/ARCHITECTURE.md`, section "Search agent loop" | the text + the flowchart | the design in words; every change above is described there |
| 2 | `run_agent.py` `run_agent_loop` | 20 lines | how the CLI flags reach `agent_loop.run(goal, max_steps, dry_run)` |
| 3 | `jobhunter/agent_loop/graph.py` `run` | whole function | the run from start to end: models, profile, memory, the loop, saving, stats |
| 4 | `jobhunter/prompts.py` `AGENT_SYSTEM` (+ `AGENT_START`, `AGENT_MEMORY`) | the prompt text | what the model is told: tools, budget, batching, "you pick, the scorer scores" |
| 5 | `graph.py` `build_graph` | the 4 inner functions | the loop: `agent_node`, `tools_node` (counts `ctx.turn`), `after_agent` (nudge / `said_done`), `after_tools` (goal / step limit) |
| 6 | `jobhunter/agent_loop/tools.py` `AgentContext` | the fields + comments | the shared state of one run: candidates, read, matches, query_log, dry_groups, scorer, scorer_down, linkedin_blocked |
| 7 | `tools.py` `make_tools` | the 4 tools | what the model can call and the argument schemas (`SearchArgs`, `ReadArgs`, `SaveArgs`) |
| 8 | `tools.py` `search_jobs` | the main tool | budget (`is_free`), group cap (`group_cap`), LinkedIn block (`jobspy_sites`), fetch, dedupe + filters, `_add_candidate` (#1), query log (#4) |
| 9 | `tools.py` `read_posting` | | records the turn of the read (for the same-turn guard), checks LinkedIn "closed" |
| 10 | `tools.py` `save_match` + `score_job` | the guardrails in order | unknown, already saved (one retry if unscored), unread, too many years, closed, not junior, same turn, then the scorer, the years backstop and the scorer-down message (#2, #3, fix) |
| 11 | `jobhunter/matcher.py` `llm_score` | | the regular scoring call the agent now reuses (prompt in `build_messages`; `fatal_llm_error` stops retries on billing / auth errors from any provider) |
| 12 | `graph.py` `trim_search`, `said_done`, `trim_reply`, `compact_history` | | what the model sees each turn (#6) |
| 13 | `jobhunter/agent_loop/memory.py` (whole file) | | `query_stats` writes the history; `memory_text`, `group_history`, `dry_groups` read it (#4, #7) |
| 14 | `graph.py` `role_groups_text`, `initial_messages` | | how memory and group history get into the first messages |
| 15 | `graph.py` `result_rows` | | what gets stored per job: scorer result, or pre-score + agent reason |
| 16 | `scripts/agent_report.py` (whole file) | | the precision report (#5) |
| 17 | `tests/test_agent_loop.py` | `ScriptedModel` at the top, then any test | each test is a small story: scripted model turns, then asserts on what happened |

Tip: the tests are the fastest way to see a feature work. Search the test file for the feature name:
`test_same_role_on_two_sources_is_kept_once` (#1), `test_batched_reads_...` (#2),
`test_saved_jobs_are_scored_by_the_pipeline_scorer` (#3), `test_next_run_is_told_which_queries_worked` (#4),
`test_agent_report_...` in `tests/test_db.py` (#5), `test_history_drops_read_rows_...` (#6),
`test_dry_groups_...` and `test_only_a_done_reply_...` (#7).

### 3.3 Where each change lives

| # | Feature | Files and functions |
|---|---|---|
| 1 | duplicates | `tools._add_candidate` |
| 2 | batching, free searches | `prompts.AGENT_SYSTEM` ("Work in batches"), `graph.tools_node` (`ctx.turn`), `tools.read_posting`, `tools.save_match` (same-turn guard), `tools.is_free`, `graph.compact_history` |
| 3 | scorer | `graph.scorer_config`, `graph.run`, `tools.score_job`, `tools.save_match`, `graph.result_rows`, `config.yaml agent.scorer` |
| 4 | memory | `memory.query_stats`, `memory.agent_runs`, `memory.past_queries`, `memory.memory_text`, `prompts.AGENT_MEMORY`, `config.yaml agent.memory_runs` |
| 5 | report | `scripts/agent_report.py` |
| 6 | smaller context | `graph.trim_search`, `graph.trim_reply`, `graph.compact_history`, `tools.COVERAGE_NOTE` |
| 7 | dry groups, DONE | `memory.group_history`, `memory.dry_groups`, `tools.group_cap`, `graph.role_groups_text`, `prompts.GROUP_HISTORY_NOTE` / `DRY_GROUPS_NOTE`, `graph.said_done`, `config.yaml agent.dry_group_searches` |
| fix | billing errors, re-saves, LinkedIn 429 | `matcher.fatal_llm_error`, `tools.score_job`, `tools.save_match`, `tools.jobspy_sites`, `tools._fetch` |

### 3.4 Words used in the code

| Word | Meaning |
|---|---|
| turn / step | one model call. `steps` counts them against `max_steps`; `ctx.turn` counts tool batches |
| candidate | a new job that passed dedupe and the filters in this run (`ctx.candidates`) |
| pre-score | free keyword score 0-100 (TF-IDF + skill overlap), shown as "fit" in search results |
| scorer | the regular search's LLM scoring call (`matcher.llm_score`), now also used for agent picks |
| strong match | saved job whose scorer score >= `agent.min_match_score` (70); counts toward the goal |
| role group | a kind of job from `agent.role_groups` (Data, Software, NOC / SOC ...); `query_groups` maps a query to its groups |
| dry group | a group with no strong match in its recent searches: 1 search per run |
| nudge | one extra message asking the model to continue when it stops before the goal |
| `scored_by` | who scored a stored job: `agent:<model>` (agent pick, scored by that model: the scorer, not the agent), `agent:heuristic` (agent pick whose scoring failed: pre-score, scored by the next pipeline run with an LLM), `llm:<model>` (regular search), `heuristic` (pre-score only) |
