# Graph Report - .  (2026-10-25)

## Corpus Check
- 31 files · ~148,659 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1285 nodes · 2834 edges · 79 communities (70 shown, 9 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.67)
- Token cost: 127,989 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_Job Filters and Experience|Job Filters and Experience]]
- [[_COMMUNITY_CV Profile and Handoff|CV Profile and Handoff]]
- [[_COMMUNITY_Agent Loop Tests|Agent Loop Tests]]
- [[_COMMUNITY_Dashboard and DB Tests|Dashboard and DB Tests]]
- [[_COMMUNITY_SQLite Storage|SQLite Storage]]
- [[_COMMUNITY_Job Model and Pipeline Tests|Job Model and Pipeline Tests]]
- [[_COMMUNITY_Figma Light Screens|Figma Light Screens]]
- [[_COMMUNITY_ATS Board Collectors|ATS Board Collectors]]
- [[_COMMUNITY_CV and Skills Tests|CV and Skills Tests]]
- [[_COMMUNITY_Named Users|Named Users]]
- [[_COMMUNITY_Collector Tests|Collector Tests]]
- [[_COMMUNITY_Collector Registry and SerpAPI|Collector Registry and SerpAPI]]
- [[_COMMUNITY_Config Loading|Config Loading]]
- [[_COMMUNITY_Remote Job Boards|Remote Job Boards]]
- [[_COMMUNITY_Fixture-based Source Tests|Fixture-based Source Tests]]
- [[_COMMUNITY_Matcher Tests|Matcher Tests]]
- [[_COMMUNITY_Search Pipeline Concepts|Search Pipeline Concepts]]
- [[_COMMUNITY_Search Pipeline Nodes|Search Pipeline Nodes]]
- [[_COMMUNITY_Project Docs and Conventions|Project Docs and Conventions]]
- [[_COMMUNITY_Plugin Panel Parsing|Plugin Panel Parsing]]
- [[_COMMUNITY_Dashboard User Forms|Dashboard User Forms]]
- [[_COMMUNITY_Run Lock and Stop|Run Lock and Stop]]
- [[_COMMUNITY_Agent Loop Runner|Agent Loop Runner]]
- [[_COMMUNITY_JobSpy Collector|JobSpy Collector]]
- [[_COMMUNITY_Figma Night Screens|Figma Night Screens]]
- [[_COMMUNITY_Agent Loop Graph|Agent Loop Graph]]
- [[_COMMUNITY_Posting Details Fetcher|Posting Details Fetcher]]
- [[_COMMUNITY_Matcher Scoring|Matcher Scoring]]
- [[_COMMUNITY_UI Components and Theme|UI Components and Theme]]
- [[_COMMUNITY_Scoring and Status Concepts|Scoring and Status Concepts]]
- [[_COMMUNITY_Company Sync Script|Company Sync Script]]
- [[_COMMUNITY_Board Check Workday Comeet|Board Check Workday Comeet]]
- [[_COMMUNITY_vLLM and Docker Overlays|vLLM and Docker Overlays]]
- [[_COMMUNITY_CLI Entry Point|CLI Entry Point]]
- [[_COMMUNITY_Handoff Tests|Handoff Tests]]
- [[_COMMUNITY_Getro Collector|Getro Collector]]
- [[_COMMUNITY_CV Tailoring Agent|CV Tailoring Agent]]
- [[_COMMUNITY_CV Personalization Tests|CV Personalization Tests]]
- [[_COMMUNITY_Multi-user and Feedback|Multi-user and Feedback]]
- [[_COMMUNITY_Dashboard Tabs|Dashboard Tabs]]
- [[_COMMUNITY_Dashboard Design System|Dashboard Design System]]
- [[_COMMUNITY_LLM Provider|LLM Provider]]
- [[_COMMUNITY_Desktop Notifications|Desktop Notifications]]
- [[_COMMUNITY_Plugin Guard Rules|Plugin Guard Rules]]
- [[_COMMUNITY_Headless Auto-Tailor|Headless Auto-Tailor]]
- [[_COMMUNITY_UI Component Helpers|UI Component Helpers]]
- [[_COMMUNITY_Board Check ATS|Board Check ATS]]
- [[_COMMUNITY_Sidebar Preferences|Sidebar Preferences]]
- [[_COMMUNITY_Job Sources Skill|Job Sources Skill]]
- [[_COMMUNITY_Tailoring and Handoff Docs|Tailoring and Handoff Docs]]
- [[_COMMUNITY_Company Boards Config|Company Boards Config]]
- [[_COMMUNITY_Agent Memory and Precision|Agent Memory and Precision]]
- [[_COMMUNITY_Cross-source Dedupe|Cross-source Dedupe]]
- [[_COMMUNITY_Run Controls|Run Controls]]
- [[_COMMUNITY_Light Dashboard Screenshot|Light Dashboard Screenshot]]
- [[_COMMUNITY_Filters and Guardrails Docs|Filters and Guardrails Docs]]
- [[_COMMUNITY_Config Overlay Tests|Config Overlay Tests]]
- [[_COMMUNITY_Handoff and Isolation|Handoff and Isolation]]
- [[_COMMUNITY_Render Compare Tool|Render Compare Tool]]
- [[_COMMUNITY_CV Sent Controls|CV Sent Controls]]
- [[_COMMUNITY_Plugin State Types|Plugin State Types]]
- [[_COMMUNITY_User Switching|User Switching]]
- [[_COMMUNITY_Test Conftest|Test Conftest]]
- [[_COMMUNITY_SerpAPI Tests|SerpAPI Tests]]
- [[_COMMUNITY_Figma Reference App|Figma Reference App]]
- [[_COMMUNITY_Sparkles Icon|Sparkles Icon]]
- [[_COMMUNITY_vLLM Serve Script|vLLM Serve Script]]
- [[_COMMUNITY_Run Start|Run Start]]
- [[_COMMUNITY_User Search Config|User Search Config]]
- [[_COMMUNITY_Requirements Files|Requirements Files]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Package Init|Package Init]]

## God Nodes (most connected - your core abstractions)
1. `Job` - 81 edges
2. `load_config()` - 54 edges
3. `CollectorResult` - 50 edges
4. `AgentContext` - 31 edges
5. `clean()` - 28 edges
6. `ScriptedModel` - 27 edges
7. `to_iso()` - 26 edges
8. `connect()` - 25 edges
9. `junior_reason()` - 22 edges
10. `use()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `lever()` --calls--> `fetch_lever()`  [EXTRACTED]
  scripts/check_boards.py → jobhunter/collectors/ats.py
- `comeet()` --calls--> `fetch_comeet()`  [EXTRACTED]
  scripts/check_boards.py → jobhunter/collectors/ats.py
- `Job` --uses--> `CollectorResult`  [INFERRED]
  tests/test_collectors.py → jobhunter/collectors/base.py
- `FakeLLM` --uses--> `CollectorResult`  [INFERRED]
  tests/test_pipeline.py → jobhunter/collectors/base.py
- `test_html_to_text_unescapes_greenhouse_style()` --calls--> `html_to_text()`  [EXTRACTED]
  tests/test_collectors.py → jobhunter/collectors/base.py

## Import Cycles
- 1-file cycle: `jobhunter/collectors/serpapi.py -> jobhunter/collectors/serpapi.py`
- 1-file cycle: `dashboard.py -> dashboard.py`
- 2-file cycle: `dashboard.py -> jobhunter/db.py -> dashboard.py`
- 3-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/db.py -> dashboard.py`
- 3-file cycle: `dashboard.py -> jobhunter/personalize.py -> jobhunter/filters.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/cv.py -> jobhunter/db.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/matcher.py -> jobhunter/db.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/matcher.py -> jobhunter/filters.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/users.py -> jobhunter/cv.py -> jobhunter/db.py -> dashboard.py`

## Hyperedges (group relationships)
- **Three-stage scoring: rule filter -> pre-score -> LLM score** — docs_architecture_rule_filter, docs_architecture_prescore, docs_architecture_llm_score, docs_architecture_jobmatch, docs_architecture_fixed_pipeline [EXTRACTED 1.00]
- **JOBHUNTER_CONFIG overlay files merged over config.yaml** — config, config_vllm, config_docker, config_docker_lmstudio, docs_architecture_config_overlay [EXTRACTED 1.00]
- **Smart agent PR #6 improvements** — docs_smart_agent_guide_pr6, docs_architecture_agent_memory, docs_architecture_dry_role_groups, docs_architecture_compact_history, docs_architecture_agent_picks_scorer_scores, docs_architecture_agent_report [EXTRACTED 1.00]

## Communities (79 total, 9 thin omitted)

### Community 0 - "Agent Loop Tools"
Cohesion: 0.05
Nodes (70): agent_runs(), dry_groups(), group_history(), memory_text(), past_queries(), query_stats(), Memory across agent runs: which queries led to saved jobs. Each run stores its p, Per search of this run: what it found, and how many of its jobs were read / save (+62 more)

### Community 1 - "Job Filters and Experience"
Cohesion: 0.06
Nodes (72): date, age_ok(), contains_any(), drop_reason(), excluded_title(), experience_ok(), filter_jobs(), is_israel() (+64 more)

### Community 2 - "CV Profile and Handoff"
Cohesion: 0.07
Nodes (61): active_user(), The user this process works for; "" is the owner. The dashboard passes users exp, apply_overrides(), CVError, extract_heuristic(), extract_with_llm(), file_hash(), find_cv() (+53 more)

### Community 3 - "Agent Loop Tests"
Cohesion: 0.09
Nodes (48): CandidateProfile, call(), calls(), env(), Replays a fixed list of replies; records the messages it was shown. As the score, One model turn with several tool calls: calls(("read_posting", {...}), ("read_po, A context where `job` was found and read in an earlier tool turn., read_ctx() (+40 more)

### Community 4 - "Dashboard and DB Tests"
Cohesion: 0.08
Nodes (36): Job, _app(), _launch(), _Ok, A reload (e.g. the theme switch) keeps filters and the run mode., The owner with one job and a user created from a CV with two jobs of their own., test_agent_mode_blocks_run_when_local_model_server_is_down(), test_agent_mode_checks_lm_studio_not_vllm_with_the_vllm_overlay() (+28 more)

### Community 5 - "SQLite Storage"
Cohesion: 0.12
Nodes (41): Connection, _add_column(), all_jobs(), backfill_required_years(), connect(), db_path(), _decode(), _dumps() (+33 more)

### Community 6 - "Job Model and Pipeline Tests"
Cohesion: 0.08
Nodes (25): collect_techmap(), parse_techmap(), Israeli Tech Map daily job lists (https://github.com/mluggy/techmap, ODbL v1.0)., Any, CollectorResult, Job, _clean_url(), Job (+17 more)

### Community 7 - "Figma Light Screens"
Cohesion: 0.07
Nodes (36): Dashboard Dark Mode Screenshot, Hebrew RTL Layout, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, score, sent, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Night Dark Theme (teal accent), Sidebar Filters (search text, min score slider, source select, location), Sidebar Run Controls (find next job button, smart agent toggle, last run stats) (+28 more)

### Community 8 - "ATS Board Collectors"
Cohesion: 0.17
Nodes (30): _company_name(), fetch_ashby(), fetch_comeet(), fetch_greenhouse(), fetch_lever(), fetch_smartrecruiters(), fetch_workday(), parse_ashby() (+22 more)

### Community 9 - "CV and Skills Tests"
Cohesion: 0.12
Nodes (18): _alias_pattern(), extract_skills(), load_vocab(), Path, Pattern, Skills vocabulary matcher, shared by the CV heuristic profile and the job pre-sc, Canonical skill names found in `text`, in vocabulary order., FakeLLM (+10 more)

### Community 10 - "Named Users"
Cohesion: 0.12
Nodes (26): create_user(), display_name(), list_users(), _new_id(), _owner_cv_dir(), parse_titles(), Path, Named users (e.g. a partner who wants their own search): created from an uploade (+18 more)

### Community 11 - "Collector Tests"
Cohesion: 0.09
Nodes (12): Job, test_a_429_on_the_last_search_is_still_reported(), test_company_boards_accept_workday_and_comeet_entries(), test_fill_descriptions_only_reads_jobs_without_one(), test_fill_descriptions_reports_closed_jobs(), test_fill_descriptions_stops_at_a_429(), test_html_to_text_unescapes_greenhouse_style(), test_jobspy_partial_miss_is_a_warning_not_an_error() (+4 more)

### Community 12 - "Collector Registry and SerpAPI"
Cohesion: 0.16
Nodes (22): CollectorResult, collect_getro(), collect_all(), _load(), Collector registry: {name: fn} and collect_all()., Run enabled sources in parallel (or just `only`). Returns (results, health recor, _run_one(), collect_serpapi() (+14 more)

### Community 13 - "Config Loading"
Cohesion: 0.18
Nodes (20): main(), python -m jobhunter.collectors --source ats --limit 5, data_dir(), deep_merge(), load_companies(), load_config(), overlay_paths(), Any (+12 more)

### Community 14 - "Remote Job Boards"
Cohesion: 0.23
Nodes (21): _arbeitnow(), _collect(), collect_arbeitnow(), collect_himalayas(), collect_remoteok(), collect_remotive(), collect_weworkremotely(), _dedupe_by_url() (+13 more)

### Community 15 - "Fixture-based Source Tests"
Cohesion: 0.14
Nodes (22): fixture(), assert_clean(), test_arbeitnow_keeps_remote_only(), test_ashby(), test_comeet(), test_comeet_reads_the_token_from_the_careers_page(), test_getro_board(), test_getro_pages_until_the_count() (+14 more)

### Community 16 - "Matcher Tests"
Cohesion: 0.13
Nodes (12): by_title(), cfg(), FakeLLM, job(), Stand-in for llm.with_structured_output(JobMatch); scorer sees the prompt text., test_an_auth_error_known_by_its_class_is_not_retried(), test_choices_reach_the_prompt_only_when_the_user_marked_jobs(), test_failure_returns_none_and_falls_back_to_prescore() (+4 more)

### Community 17 - "Search Pipeline Concepts"
Cohesion: 0.13
Nodes (20): agent-pipeline skill, Conditional LLM edge (llm_enabled), LangGraph search pipeline graph, No built-in scheduling, notify node (strong matches), PipelineState, run_agent.py CLI flags, cv-profile skill (+12 more)

### Community 18 - "Search Pipeline Nodes"
Cohesion: 0.19
Nodes (20): after_prescore(), build_graph(), collect_node(), _db(), dedupe_node(), filter_node(), llm_score_node(), load_profile_node() (+12 more)

### Community 19 - "Project Docs and Conventions"
Cohesion: 0.15
Nodes (18): CLAUDE.md project instructions, Collector contract: return list[Job], never raise, LLM is optional (provider: none -> heuristic scores), All LLM prompts in jobhunter/prompts.py, Project skills (job-sources, job-matching, agent-pipeline, ...), Never overwrite status/notes on re-collect or re-score, llm section: LM Studio Qwen3.8 27B, thinking off for scoring, ARCHITECTURE.md (source of truth) (+10 more)

### Community 20 - "Plugin Panel Parsing"
Cohesion: 0.19
Nodes (15): isAgentRun(), isPytest(), parsePlan(), parsePytest(), readLastRun(), readPhaseNumber(), shortTime(), toPhase() (+7 more)

### Community 21 - "Dashboard User Forms"
Cohesion: 0.13
Nodes (15): add_user_form(), claude_panel(), cv_upload_form(), force_stop(), on_stop_toggle(), profile_tab(), profile_view(), Streamlit dashboard: browse scored jobs, track applications. Hebrew UI, RTL. (+7 more)

### Community 22 - "Run Lock and Stop"
Cohesion: 0.16
Nodes (17): Where run.lock, stop.flag and run logs live. For the owner JOBHUNTER_RUN_DIR ove, run_dir(), lock_path(), pid_alive(), Path, One run at a time: <run dir>/run.lock holds the PID of the running search (pipel, PID of the run holding the lock, or None when no live run holds it., running_pid() (+9 more)

### Community 23 - "Agent Loop Runner"
Cohesion: 0.15
Nodes (18): AgentUnavailable, build_graph(), Every candidate the agent saw; the ones it saved carry the scorer's result, scor, Config whose `llm` scores the agent's picks: agent.scorer "main" = the `llm` sec, Run the agent loop once. Options: goal, max_steps, dry_run, db_path.     Return, A reply's text: the string itself, or the text blocks of provider content blocks, The reply's last line (reasoning removed) is DONE: the model says nothing promis, reply_text() (+10 more)

### Community 24 - "JobSpy Collector"
Cohesion: 0.16
Nodes (14): collect_jobspy(), employer_queries(), frame_to_jobs(), _quoted(), RateLimitWatch, LinkedIn / Indeed / Glassdoor / Google Jobs through the python-jobspy library., Notices "status code 429" in JobSpy's LinkedIn log, so a run stops asking Linked, Convert a JobSpy DataFrame (or a CSV loaded with pandas) to Jobs. (+6 more)

### Community 25 - "Figma Night Screens"
Cohesion: 0.14
Nodes (18): Figma 8:27 Dark Moody Split Screen (Jobs tab mockup), Dark "Night" Theme (near-black bg, violet accent), Hebrew RTL Tab Bar (jobs, pipeline, insights, sources, profile), Preliminary (heuristic) score label - automatic, no LLM, Job Detail Panel (big score badge, matched/missing skill chips, tip, notes, save/open buttons), Jobs Table with Score Bars (score, role, company, location, source, days, assessment, status, link), KPI Cards Row (matching jobs, new today, strong match 75+, applications submitted), Split Layout: Jobs Table + Job Detail Side Panel (+10 more)

### Community 26 - "Agent Loop Graph"
Cohesion: 0.16
Nodes (16): compact_history(), experience_limit(), initial_messages(), LoopState, Tool-using agent loop (ReAct style): the model picks the next tool until it reac, One line per group; with history, each line says what the group gave in recent r, An earlier search result without its stale coverage note and without the rows of, A model reply without <think> blocks; earlier replies are also cut to MAX_OLD_TE (+8 more)

### Community 27 - "Posting Details Fetcher"
Cohesion: 0.19
Nodes (16): fetch_posting(), fill_descriptions(), linkedin_job_id(), _linkedin_reader(), parse_posting(), Posting, Fill in missing job descriptions, so the experience rules can be checked.  Lin, Description and closed flag from a LinkedIn job page, parsed with JobSpy's own h (+8 more)

### Community 28 - "Matcher Scoring"
Cohesion: 0.21
Nodes (16): build_messages(), explanation_language(), llm_score(), preferences_text(), Any, Job, JobMatch, Stage 2 + 3: free pre-score (TF-IDF + skill overlap) and parallel LLM scoring. (+8 more)

### Community 29 - "UI Components and Theme"
Cohesion: 0.14
Nodes (11): brand_header(), current_scheme(), inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma c, dark' or 'light', as the browser actually renders it., Sidebar masthead: brand name with the sparkles mark (Figma 7:2430) and the kit b, Call once at the top of the page, after st.set_page_config. (+3 more)

### Community 30 - "Scoring and Status Concepts"
Cohesion: 0.20
Nodes (15): Jobs table with editable status, job-matching skill, Candidate choices feedback block, LLM required_years backstop, matcher.llm_score (JobMatch), Location filter (is_israel / remote_ok), Filter -> prescore -> LLM score, STATUSES constant (+7 more)

### Community 31 - "Company Sync Script"
Cohesion: 0.23
Nodes (14): add_to_yaml(), boards_in(), candidates(), download_techmap(), existing(), main(), Add Israeli companies' job boards to companies.yaml from the open Israeli Tech M, Board links on one careers page. A per-read timeout alone let slow, endless page (+6 more)

### Community 32 - "Board Check Workday Comeet"
Cohesion: 0.19
Nodes (10): israel_facets(), Workday location facet ids for Israel, as {"<facetParameter>": [ids]}.     The, _workday_search(), comeet(), check(), label(), lever(), main() (+2 more)

### Community 33 - "vLLM and Docker Overlays"
Cohesion: 0.30
Nodes (13): config.docker.yaml (vllm service + host LM Studio for agent), config.docker.lmstudio.yaml (LM Studio via host.docker.internal), config.vllm.yaml overlay (local vLLM scorer), qwen3-local served model (Qwen3-14B AWQ on vLLM), docker-compose.yml (app demo container), docker-compose.vllm.yml (vllm GPU service overlay), vllm service (vllm/vllm-openai v0.31.0), JOBHUNTER_CONFIG overlay merging (+5 more)

### Community 34 - "CLI Entry Point"
Cohesion: 0.25
Nodes (11): Context manager around run.lock. Clears a stale stop request on entry and the st, run_lock, RunLocked, Namespace, main(), print_agent_summary(), print_summary(), CLI entry point of the search agent:  python run_agent.py [--no-llm] [--sources (+3 more)

### Community 35 - "Handoff Tests"
Cohesion: 0.14
Nodes (3): A user with a CV and one scored job, all inside the temp folder., test_brief_for_heuristic_job_and_unknown_id(), user()

### Community 36 - "Getro Collector"
Cohesion: 0.23
Nodes (11): get_session(), One session: User-Agent, retry 3x with backoff on 429/5xx., fetch_board(), parse_getro(), Venture-capital portfolio job boards on Getro (e.g. Israel VC Forum: ~880 portfo, search_page(), Job, main() (+3 more)

### Community 37 - "CV Tailoring Agent"
Cohesion: 0.27
Nodes (13): cv-tailoring skill, Tailoring kit outputs (changes.md, gaps.md, cover letter), No-fabrication rule, CV Tailoring Agent graph (Phase 8), verify node (fact-check loop), Master CV schema (cv_master.yaml), Owner CV rules, Experience bank and NOT list (+5 more)

### Community 38 - "CV Personalization Tests"
Cohesion: 0.24
Nodes (12): experience_limit(), personalize(), Any, CandidateProfile, Role keywords from job titles, in the form filters.contains_any expects     ("D, The config this user's run should use. Unchanged unless `auto_from_cv` is on., role_words(), test_personalize_derives_search_from_the_cv() (+4 more)

### Community 39 - "Multi-user and Feedback"
Cohesion: 0.20
Nodes (12): matching section (llm_top_n, fetch_descriptions, feedback_examples), search.employers groups (banks, health funds, defense, IT services), cv/README (put CV here, newest wins), auto_from_cv personalization, Candidate preferences block (profile.preferences), CandidateProfile, Learning from user choices (<candidate_choices>), Stage 3 LLM score (top llm_top_n) (+4 more)

### Community 40 - "Dashboard Tabs"
Cohesion: 0.29
Nodes (12): bar(), detail_panel(), insights_tab(), jobs_tab(), load_jobs(), main(), pipeline_tab(), New status per edited row. Ticking "CV sent" marks the job applied (and records (+4 more)

### Community 41 - "Dashboard Design System"
Cohesion: 0.27
Nodes (12): dashboard-design skill, Color has meaning rule, Render-and-compare loop (compare.py), Job Hunter Dashboard Figma file, Three-layer design architecture (config.toml / tokens+css / components), Figma map, Night dark theme (8:27), Sea light theme (2:30) (+4 more)

### Community 42 - "LLM Provider"
Cohesion: 0.24
Nodes (11): load_env(), Load API keys from .env into the process environment., agent_llm_config(), get_llm(), _has_key(), llm_available(), Any, Provider-agnostic chat model. Returns None when the LLM is disabled or has no ke (+3 more)

### Community 43 - "Desktop Notifications"
Cohesion: 0.27
Nodes (10): notify_strong_matches(), Any, Optional desktop notification after a run when new strong matches were found (co, Fire-and-forget balloon notification (no extra modules needed)., Returns how many strong matches were announced (0 when disabled or none)., strong_matches(), windows_balloon(), test_announces_best_match_and_count() (+2 more)

### Community 44 - "Plugin Guard Rules"
Cohesion: 0.27
Nodes (5): BASH_RULES, checkBash(), checkFile(), isPython(), Verdict

### Community 45 - "Headless Auto-Tailor"
Cohesion: 0.36
Nodes (10): apply skill (/apply <job-id>), Unattended /apply mode, auto-tailor skill, auto_tailor_node, Never pass --bare, handoff.run_headless, subscription_env() child environment, tailoring.auto_* config (+2 more)

### Community 46 - "UI Component Helpers"
Cohesion: 0.20
Nodes (5): inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma com, Call once at the top of the page, after st.set_page_config., items in reading order (right → left in RTL): [("משרות מתאימות", 12), ...]

### Community 47 - "Board Check ATS"
Cohesion: 0.24
Nodes (4): check(), label(), main(), Validate companies.yaml: which ATS slugs are alive and how many Israel jobs each

### Community 48 - "Sidebar Preferences"
Cohesion: 0.20
Nodes (10): default_goal(), experience_toggle(), init_prefs(), pref_defaults(), Seed widget state from the URL when a widget has no state yet (widgets then take, Write non-default settings to the URL; defaults are left out to keep it short., The "experience limit" view toggle, worded for this user's limit; none when ther, save_prefs() (+2 more)

### Community 49 - "Job Sources Skill"
Cohesion: 0.29
Nodes (10): job-sources skill, Collector contract (CollectorResult, never raise), collectors/details.py description + closed-job fetch, JobSpy collector, RateLimitWatch (LinkedIn 429), Shared requests.Session (base.get_session), Job source endpoints and field mappings, Comeet careers API (+2 more)

### Community 50 - "Tailoring and Handoff Docs"
Cohesion: 0.28
Nodes (8): No-fabrication rule (only facts in cv_master.yaml), tailoring section (auto_min_score, auto_mode headless), Headless auto-tailor (claude -p /apply, Phase 9), Claude handoff brief (subscription, not API), CV Tailoring Agent (Phase 8, planned), Per-phase acceptance checks, Phase 8: CV Tailoring Agent (not started), Phase 9: Auto-tailor on the subscription

### Community 51 - "Company Boards Config"
Cohesion: 0.25
Nodes (9): companies.yaml (ATS company boards), ATS types: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Comeet, config.yaml (main settings), SerpAPI Google Jobs short query list (250/month quota), JOB_SOURCES_RESEARCH.md (additional job sources), Israeli job boards (Drushim, AllJobs, JobMaster), Microsoft Careers / eightfold ATS type, Goozali Telegram junior channels (+1 more)

### Community 52 - "Agent Memory and Precision"
Cohesion: 0.44
Nodes (9): agent section (goal, budgets, role_groups, scorer, memory_runs), Agent memory across runs (runs.stats.queries), Agent picks, scorer scores (agent.scorer main|agent), agent_report.py precision report, compact_history context trimming, Dry role groups (one search per run), Search agent loop (ReAct, --agent), PR #6 smart agent rework (7 changes) (+1 more)

### Community 53 - "Cross-source Dedupe"
Cohesion: 0.28
Nodes (8): dedupe_batch(), is_new(), Job, Dedupe: the same posting (same id) or the same role on several boards (same comp, Lower is better: company boards (full descriptions) beat JobSpy beat remote boar, Drop repeated ids; for the same company|title keep the best source (board > jobs, Not stored yet, neither as this posting nor as the same role from another board., source_priority()

### Community 54 - "Run Controls"
Cohesion: 0.36
Nodes (8): _health_url(), is_running(), local_llm_down(), True when the agent's local model server (LM Studio / vLLM base_url) does not an, Live log while a run is going; only this fragment polls, the controls stay still, run_active(), run_controls(), run_status()

### Community 55 - "Light Dashboard Screenshot"
Cohesion: 0.32
Nodes (8): Dashboard Screenshot (Light Theme), Hebrew RTL UI with Sea (light purple) theme, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, note, sent checkbox, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Minimum Match Score Slider, Sidebar: Run Search Button, Smart Agent Toggle, Filters, Dashboard Tabs (Jobs, Pipeline, Insights, Sources, Profile)

### Community 56 - "Filters and Guardrails Docs"
Cohesion: 0.38
Nodes (7): collect_company_boards(), entry_label(), _one_company(), How a companies.yaml entry is named in errors: the slug, or the Workday tenant., Fetch every company in companies.yaml. `limit` caps jobs kept per company., Any, CollectorResult

### Community 57 - "Config Overlay Tests"
Cohesion: 0.33
Nodes (7): filters section (junior/senior keywords, max_required_years: 0), Agent guardrails in code (budgets, read-before-save, hidden filtered jobs), Experience limit (junior_reason, years_over_limit backstops), JobMatch structured LLM output, Stage 1 rule filter (location/role/seniority/age), LinkedIn closed-job page fixture, LinkedIn open-job page fixture

### Community 58 - "Handoff and Isolation"
Cohesion: 0.52
Nodes (6): overlay(), test_a_missing_overlay_is_a_clear_error(), test_docker_overlay_points_the_scorer_at_compose_and_the_agent_at_the_host(), test_no_overlay_is_config_yaml_as_is(), test_overlays_merge_in_order_over_config_yaml(), test_vllm_config_scores_on_vllm_and_leaves_the_agent_on_lm_studio()

### Community 59 - "Render Compare Tool"
Cohesion: 0.33
Nodes (6): Run lock (runlock.py, run.lock), handoff.py per-job brief, job-dashboard skill, Prepare application with Claude button, Per-session user/DB selection, Test isolation via env vars (JOBHUNTER_DB/RUN_DIR/USERS_DIR)

### Community 60 - "CV Sent Controls"
Cohesion: 0.60
Nodes (5): Path, main(), Render the running dashboard and put it next to the Figma reference.  Usage (fro, render(), side_by_side()

### Community 61 - "Plugin State Types"
Cohesion: 0.33
Nodes (6): Two short lines; every number is isolated with <bdi> so Hebrew and digits keep t, The "CV sent" button, or when it was sent and an undo., run_summary_html(), sent_controls(), to_il(), datetime

### Community 62 - "User Switching"
Cohesion: 0.33
Nodes (5): LastRun, Phase, PluginState, Progress, Tests

### Community 63 - "Test Conftest"
Cohesion: 0.40
Nodes (5): on_add_user(), owner_label(), Start the other user's view clean: filters, table edits and run state belong to, switch_user(), user_picker()

### Community 65 - "Figma Reference App"
Cohesion: 0.50
Nodes (4): _fake_serpapi(), Record the queries sent to SerpAPI; answer each with the sample fixture., test_serpapi_falls_back_to_search_queries(), test_serpapi_uses_its_own_query_list()

## Knowledge Gaps
- **66 isolated node(s):** `BASH_RULES`, `Verdict`, `RUN`, `EMPTY`, `progress` (+61 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Job` connect `Job Model and Pipeline Tests` to `Handoff Tests`, `Getro Collector`, `CV Personalization Tests`, `ATS Board Collectors`, `Named Users`, `Collector Tests`, `Collector Registry and SerpAPI`, `Remote Job Boards`, `Cross-source Dedupe`, `JobSpy Collector`, `Filters and Guardrails Docs`, `Posting Details Fetcher`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Why does `load_config()` connect `Config Loading` to `Agent Loop Tools`, `Job Filters and Experience`, `CV Profile and Handoff`, `Agent Loop Tests`, `Dashboard and DB Tests`, `Job Model and Pipeline Tests`, `Named Users`, `Matcher Tests`, `Search Pipeline Nodes`, `Dashboard User Forms`, `Agent Loop Runner`, `Agent Loop Graph`, `Company Sync Script`, `CV Personalization Tests`, `LLM Provider`, `Handoff and Isolation`, `Test Conftest`, `SerpAPI Tests`, `Requirements Files`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `Dashboard Dark Mode Screenshot` connect `Figma Light Screens` to `Dashboard User Forms`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `Job` (e.g. with `CollectorResult` and `Posting`) actually correct?**
  _`Job` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `CollectorResult` (e.g. with `Job` and `RateLimitWatch`) actually correct?**
  _`CollectorResult` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `AgentContext` (e.g. with `AgentUnavailable` and `LoopState`) actually correct?**
  _`AgentContext` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Visual prototype of Figma frame 2:30 'Dashboard / Jobs' with static sample data.`, `Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma com`, `Call once at the top of the page, after st.set_page_config.` to the rest of the system?**
  _283 weakly-connected nodes found - possible documentation gaps or missing edges._