# Graph Report - .  (2026-11-23)

## Corpus Check
- 13 files · ~150,701 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1285 nodes · 2744 edges · 84 communities (74 shown, 10 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 172 edges (avg confidence: 0.68)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_CV Profile and Handoff|CV Profile and Handoff]]
- [[_COMMUNITY_Agent Loop Tests|Agent Loop Tests]]
- [[_COMMUNITY_CV and Skills Tests|CV and Skills Tests]]
- [[_COMMUNITY_SQLite Storage|SQLite Storage]]
- [[_COMMUNITY_Agent Loop Runner|Agent Loop Runner]]
- [[_COMMUNITY_Figma Light Screens|Figma Light Screens]]
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_Job Filters and Experience|Job Filters and Experience]]
- [[_COMMUNITY_Job Model and Pipeline Tests|Job Model and Pipeline Tests]]
- [[_COMMUNITY_Named Users|Named Users]]
- [[_COMMUNITY_Dashboard and DB Tests|Dashboard and DB Tests]]
- [[_COMMUNITY_Collector Tests|Collector Tests]]
- [[_COMMUNITY_Matcher Scoring|Matcher Scoring]]
- [[_COMMUNITY_Remote Job Boards|Remote Job Boards]]
- [[_COMMUNITY_Config Loading|Config Loading]]
- [[_COMMUNITY_CV Personalization Tests|CV Personalization Tests]]
- [[_COMMUNITY_CLI Entry Point|CLI Entry Point]]
- [[_COMMUNITY_Dashboard User Forms|Dashboard User Forms]]
- [[_COMMUNITY_Search Pipeline Nodes|Search Pipeline Nodes]]
- [[_COMMUNITY_Fixture-based Source Tests|Fixture-based Source Tests]]
- [[_COMMUNITY_Matcher Tests|Matcher Tests]]
- [[_COMMUNITY_Search Pipeline Concepts|Search Pipeline Concepts]]
- [[_COMMUNITY_Dashboard and DB Tests|Dashboard and DB Tests]]
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_Plugin Panel Parsing|Plugin Panel Parsing]]
- [[_COMMUNITY_ATS Board Collectors|ATS Board Collectors]]
- [[_COMMUNITY_Board Check Workday Comeet|Board Check Workday Comeet]]
- [[_COMMUNITY_Collector Registry and SerpAPI|Collector Registry and SerpAPI]]
- [[_COMMUNITY_JobSpy Collector|JobSpy Collector]]
- [[_COMMUNITY_Figma Night Screens|Figma Night Screens]]
- [[_COMMUNITY_Posting Details Fetcher|Posting Details Fetcher]]
- [[_COMMUNITY_Dashboard Tabs|Dashboard Tabs]]
- [[_COMMUNITY_UI Components and Theme|UI Components and Theme]]
- [[_COMMUNITY_vLLM and Docker Overlays|vLLM and Docker Overlays]]
- [[_COMMUNITY_Company Sync Script|Company Sync Script]]
- [[_COMMUNITY_Project Docs and Conventions|Project Docs and Conventions]]
- [[_COMMUNITY_Collector Registry and SerpAPI|Collector Registry and SerpAPI]]
- [[_COMMUNITY_Config and Filter Settings|Config and Filter Settings]]
- [[_COMMUNITY_Scoring and Status Concepts|Scoring and Status Concepts]]
- [[_COMMUNITY_Handoff Tests|Handoff Tests]]
- [[_COMMUNITY_CV Tailoring Agent|CV Tailoring Agent]]
- [[_COMMUNITY_Job Filters and Experience|Job Filters and Experience]]
- [[_COMMUNITY_Getro Collector|Getro Collector]]
- [[_COMMUNITY_Tailoring and Handoff Docs|Tailoring and Handoff Docs]]
- [[_COMMUNITY_Sidebar Preferences|Sidebar Preferences]]
- [[_COMMUNITY_Dashboard Design System|Dashboard Design System]]
- [[_COMMUNITY_Desktop Notifications|Desktop Notifications]]
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_Plugin Guard Rules|Plugin Guard Rules]]
- [[_COMMUNITY_Job Filters and Experience|Job Filters and Experience]]
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_Headless Auto-Tailor|Headless Auto-Tailor]]
- [[_COMMUNITY_UI Component Helpers|UI Component Helpers]]
- [[_COMMUNITY_Board Check ATS|Board Check ATS]]
- [[_COMMUNITY_Job Sources Skill|Job Sources Skill]]
- [[_COMMUNITY_Getro Collector|Getro Collector]]
- [[_COMMUNITY_Agent Memory and Precision|Agent Memory and Precision]]
- [[_COMMUNITY_Cross-source Dedupe|Cross-source Dedupe]]
- [[_COMMUNITY_Run Lock and Stop|Run Lock and Stop]]
- [[_COMMUNITY_Run Controls|Run Controls]]
- [[_COMMUNITY_Light Dashboard Screenshot|Light Dashboard Screenshot]]
- [[_COMMUNITY_Filters and Guardrails Docs|Filters and Guardrails Docs]]
- [[_COMMUNITY_Company Boards Config|Company Boards Config]]
- [[_COMMUNITY_Render Compare Tool|Render Compare Tool]]
- [[_COMMUNITY_CV Sent Controls|CV Sent Controls]]
- [[_COMMUNITY_User Switching|User Switching]]
- [[_COMMUNITY_Test Conftest|Test Conftest]]
- [[_COMMUNITY_Job Filters and Experience|Job Filters and Experience]]
- [[_COMMUNITY_SerpAPI Tests|SerpAPI Tests]]
- [[_COMMUNITY_Figma Reference App|Figma Reference App]]
- [[_COMMUNITY_Sparkles Icon|Sparkles Icon]]
- [[_COMMUNITY_vLLM Serve Script|vLLM Serve Script]]
- [[_COMMUNITY_Run Start|Run Start]]
- [[_COMMUNITY_Requirements Files|Requirements Files]]
- [[_COMMUNITY_Config Overlay Tests|Config Overlay Tests]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Embedding Pre-score Idea|Embedding Pre-score Idea]]
- [[_COMMUNITY_Agent Precision Metric|Agent Precision Metric]]
- [[_COMMUNITY_Skills Vocabulary|Skills Vocabulary]]

## God Nodes (most connected - your core abstractions)
1. `Job` - 73 edges
2. `CollectorResult` - 45 edges
3. `load_config()` - 44 edges
4. `AgentContext` - 31 edges
5. `clean()` - 28 edges
6. `ScriptedModel` - 27 edges
7. `to_iso()` - 26 edges
8. `connect()` - 25 edges
9. `junior_reason()` - 23 edges
10. `use()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `Fixed LangGraph pipeline` --semantically_similar_to--> `LangGraph StateGraph pipeline`  [INFERRED] [semantically similar]
  README.md → docs/ARCHITECTURE.md
- `Agent loop (--agent)` --semantically_similar_to--> `Search agent loop (ReAct, guardrails in code)`  [INFERRED] [semantically similar]
  README.md → docs/ARCHITECTURE.md
- `Multi-user model (owner + users/<id>)` --semantically_similar_to--> `Several users on one PC (auto_from_cv)`  [INFERRED] [semantically similar]
  CLAUDE.md → docs/ARCHITECTURE.md
- `Claude handoff (brief, subscription)` --semantically_similar_to--> `Claude handoff (brief.md, subscription env)`  [INFERRED] [semantically similar]
  README.md → docs/ARCHITECTURE.md
- `Job` --uses--> `CollectorResult`  [INFERRED]
  tests/test_collectors.py → jobhunter/collectors/base.py

## Import Cycles
- 1-file cycle: `jobhunter/collectors/serpapi.py -> jobhunter/collectors/serpapi.py`
- 1-file cycle: `dashboard.py -> dashboard.py`
- 2-file cycle: `dashboard.py -> jobhunter/db.py -> dashboard.py`
- 3-file cycle: `dashboard.py -> jobhunter/personalize.py -> jobhunter/filters.py -> dashboard.py`
- 3-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/db.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/users.py -> jobhunter/cv.py -> jobhunter/db.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/matcher.py -> jobhunter/db.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/matcher.py -> jobhunter/filters.py -> dashboard.py`
- 4-file cycle: `dashboard.py -> jobhunter/handoff.py -> jobhunter/cv.py -> jobhunter/db.py -> dashboard.py`

## Hyperedges (group relationships)
- **Three-stage scoring flow** — docs_architecture_three_stage_scoring, docs_architecture_experience_limit, docs_architecture_prescore, docs_architecture_llm_score [EXTRACTED 0.95]
- **Claude subscription handoff and tailoring flow** — docs_architecture_claude_handoff, docs_architecture_headless_auto_tailor, docs_architecture_cv_tailoring_agent, readme_claude_handoff [INFERRED 0.85]
- **Agent loop guardrails** — docs_architecture_search_agent_loop, docs_architecture_role_groups, docs_architecture_agent_memory, docs_architecture_stop_run [INFERRED 0.85]

## Communities (84 total, 10 thin omitted)

### Community 0 - "CV Profile and Handoff"
Cohesion: 0.07
Nodes (60): active_user(), The user this process works for; "" is the owner. The dashboard passes users exp, apply_overrides(), CVError, extract_heuristic(), extract_with_llm(), file_hash(), find_cv() (+52 more)

### Community 1 - "Agent Loop Tests"
Cohesion: 0.09
Nodes (48): CandidateProfile, call(), calls(), env(), Replays a fixed list of replies; records the messages it was shown. As the score, One model turn with several tool calls: calls(("read_posting", {...}), ("read_po, A context where `job` was found and read in an earlier tool turn., read_ctx() (+40 more)

### Community 2 - "CV and Skills Tests"
Cohesion: 0.07
Nodes (35): load_env(), Load API keys from .env into the process environment., agent_llm_config(), get_llm(), _has_key(), llm_available(), Any, Provider-agnostic chat model. Returns None when the LLM is disabled or has no ke (+27 more)

### Community 3 - "SQLite Storage"
Cohesion: 0.12
Nodes (41): Connection, _add_column(), all_jobs(), backfill_required_years(), connect(), db_path(), _decode(), _dumps() (+33 more)

### Community 4 - "Agent Loop Runner"
Cohesion: 0.09
Nodes (34): AgentUnavailable, build_graph(), compact_history(), experience_limit(), initial_messages(), LoopState, Tool-using agent loop (ReAct style): the model picks the next tool until it reac, One line per group; with history, each line says what the group gave in recent r (+26 more)

### Community 5 - "Figma Light Screens"
Cohesion: 0.07
Nodes (36): Dashboard Dark Mode Screenshot, Hebrew RTL Layout, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, score, sent, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Night Dark Theme (teal accent), Sidebar Filters (search text, min score slider, source select, location), Sidebar Run Controls (find next job button, smart agent toggle, last run stats) (+28 more)

### Community 6 - "Agent Loop Tools"
Cohesion: 0.14
Nodes (30): _add_candidate(), AgentContext, coverage_note(), _fetch(), get_profile(), group_cap(), is_free(), jobspy_sites() (+22 more)

### Community 7 - "Job Filters and Experience"
Cohesion: 0.12
Nodes (29): experience_ok(), junior_reason(), over_limit_score(), Largest 'N years' lower bound mentioned in the text (0 if none).     Reads "3+, Junior mode: keep jobs that state no more than `max_years` of required experienc, Score of a stored job whose posting asks for `years` of experience, more than th, Why a job is not a junior job ("senior" / "experience" / "unverified"), or None, required_years() (+21 more)

### Community 8 - "Job Model and Pipeline Tests"
Cohesion: 0.10
Nodes (16): Job, filter_jobs(), Returns (kept jobs, drop counts by reason)., test_filter_jobs_counts_reasons(), test_israel_and_remote_switches(), FakeLLM, jobs(), test_closed_linkedin_jobs_are_not_saved() (+8 more)

### Community 9 - "Named Users"
Cohesion: 0.12
Nodes (26): create_user(), display_name(), list_users(), _new_id(), _owner_cv_dir(), parse_titles(), Path, Named users (e.g. a partner who wants their own search): created from an uploade (+18 more)

### Community 10 - "Dashboard and DB Tests"
Cohesion: 0.15
Nodes (22): _app(), _launch(), _Ok, A reload (e.g. the theme switch) keeps filters and the run mode., The owner with one job and a user created from a CV with two jobs of their own., test_agent_mode_blocks_run_when_local_model_server_is_down(), test_agent_mode_checks_lm_studio_not_vllm_with_the_vllm_overlay(), test_agent_mode_runs_agent_with_chosen_goal() (+14 more)

### Community 11 - "Collector Tests"
Cohesion: 0.09
Nodes (12): Job, test_a_429_on_the_last_search_is_still_reported(), test_company_boards_accept_workday_and_comeet_entries(), test_fill_descriptions_only_reads_jobs_without_one(), test_fill_descriptions_reports_closed_jobs(), test_fill_descriptions_stops_at_a_429(), test_html_to_text_unescapes_greenhouse_style(), test_jobspy_partial_miss_is_a_warning_not_an_error() (+4 more)

### Community 12 - "Matcher Scoring"
Cohesion: 0.14
Nodes (23): The pipeline's scoring prompt and rubric (matcher.llm_score), so agent picks and, score_job(), JobMatch, build_messages(), explanation_language(), fatal_llm_error(), llm_score(), preferences_text() (+15 more)

### Community 13 - "Remote Job Boards"
Cohesion: 0.22
Nodes (23): html_to_text(), HTML (or HTML-escaped HTML, as Greenhouse sends) -> plain text., _arbeitnow(), _collect(), collect_arbeitnow(), collect_himalayas(), collect_remoteok(), collect_remotive() (+15 more)

### Community 14 - "Config Loading"
Cohesion: 0.17
Nodes (22): main(), python -m jobhunter.collectors --source ats --limit 5, data_dir(), deep_merge(), load_companies(), load_config(), overlay_paths(), Any (+14 more)

### Community 15 - "CV Personalization Tests"
Cohesion: 0.15
Nodes (19): CandidateProfile, _clean_url(), Core data models: Job (collected), CandidateProfile (from CV), JobMatch (from LL, Lower-case and drop tracking params (utm_*, refId, trackingId, trk)., experience_limit(), _not_in(), personalize(), Any (+11 more)

### Community 16 - "CLI Entry Point"
Cohesion: 0.15
Nodes (18): lock_path(), pid_alive(), Path, One run at a time: <run dir>/run.lock holds the PID of the running search (pipel, PID of the run holding the lock, or None when no live run holds it., Context manager around run.lock. Clears a stale stop request on entry and the st, run_lock, RunLocked (+10 more)

### Community 17 - "Dashboard User Forms"
Cohesion: 0.12
Nodes (17): add_user_form(), claude_panel(), cv_upload_form(), force_stop(), on_stop_toggle(), profile_tab(), profile_view(), Streamlit dashboard: browse scored jobs, track applications. Hebrew UI, RTL. (+9 more)

### Community 18 - "Search Pipeline Nodes"
Cohesion: 0.18
Nodes (21): after_prescore(), build_graph(), collect_node(), _db(), dedupe_node(), filter_node(), llm_score_node(), load_profile_node() (+13 more)

### Community 19 - "Fixture-based Source Tests"
Cohesion: 0.14
Nodes (22): fixture(), assert_clean(), test_arbeitnow_keeps_remote_only(), test_ashby(), test_comeet(), test_comeet_reads_the_token_from_the_careers_page(), test_getro_board(), test_getro_pages_until_the_count() (+14 more)

### Community 20 - "Matcher Tests"
Cohesion: 0.13
Nodes (12): by_title(), cfg(), FakeLLM, job(), Stand-in for llm.with_structured_output(JobMatch); scorer sees the prompt text., test_an_auth_error_known_by_its_class_is_not_retried(), test_choices_reach_the_prompt_only_when_the_user_marked_jobs(), test_failure_returns_none_and_falls_back_to_prescore() (+4 more)

### Community 21 - "Search Pipeline Concepts"
Cohesion: 0.13
Nodes (20): agent-pipeline skill, Conditional LLM edge (llm_enabled), LangGraph search pipeline graph, No built-in scheduling, notify node (strong matches), PipelineState, run_agent.py CLI flags, cv-profile skill (+12 more)

### Community 22 - "Dashboard and DB Tests"
Cohesion: 0.16
Nodes (16): job_from_row(), Job, A stored jobs row back to the Job the collectors produced., get(), make_row(), test_agent_report_compares_picks_with_what_the_user_did(), test_backfill_required_years(), test_env_override() (+8 more)

### Community 23 - "Agent Loop Tools"
Cohesion: 0.14
Nodes (18): agent_runs(), dry_groups(), group_history(), memory_text(), past_queries(), query_stats(), Memory across agent runs: which queries led to saved jobs. Each run stores its p, Per search of this run: what it found, and how many of its jobs were read / save (+10 more)

### Community 24 - "Plugin Panel Parsing"
Cohesion: 0.19
Nodes (15): isAgentRun(), isPytest(), parsePlan(), parsePytest(), readLastRun(), readPhaseNumber(), shortTime(), toPhase() (+7 more)

### Community 25 - "ATS Board Collectors"
Cohesion: 0.26
Nodes (19): _company_name(), fetch_ashby(), fetch_greenhouse(), fetch_smartrecruiters(), parse_ashby(), parse_comeet(), parse_greenhouse(), parse_lever() (+11 more)

### Community 26 - "Board Check Workday Comeet"
Cohesion: 0.15
Nodes (15): fetch_comeet(), fetch_lever(), fetch_workday(), israel_facets(), Workday location facet ids for Israel, as {"<facetParameter>": [ids]}.     The, Israel postings of one Workday company ({tenant, wd, site} from companies.yaml)., One Comeet company, "<slug>/<uid>" from its careers URL comeet.com/jobs/<slug>/<, _workday_search() (+7 more)

### Community 27 - "Collector Registry and SerpAPI"
Cohesion: 0.19
Nodes (17): CollectorResult, collect_all(), _load(), Collector registry: {name: fn} and collect_all()., Run enabled sources in parallel (or just `only`). Returns (results, health recor, _run_one(), collect_techmap(), parse_techmap() (+9 more)

### Community 28 - "JobSpy Collector"
Cohesion: 0.16
Nodes (14): collect_jobspy(), employer_queries(), frame_to_jobs(), _quoted(), RateLimitWatch, LinkedIn / Indeed / Glassdoor / Google Jobs through the python-jobspy library., Notices "status code 429" in JobSpy's LinkedIn log, so a run stops asking Linked, Convert a JobSpy DataFrame (or a CSV loaded with pandas) to Jobs. (+6 more)

### Community 29 - "Figma Night Screens"
Cohesion: 0.14
Nodes (18): Figma 8:27 Dark Moody Split Screen (Jobs tab mockup), Dark "Night" Theme (near-black bg, violet accent), Hebrew RTL Tab Bar (jobs, pipeline, insights, sources, profile), Preliminary (heuristic) score label - automatic, no LLM, Job Detail Panel (big score badge, matched/missing skill chips, tip, notes, save/open buttons), Jobs Table with Score Bars (score, role, company, location, source, days, assessment, status, link), KPI Cards Row (matching jobs, new today, strong match 75+, applications submitted), Split Layout: Jobs Table + Job Detail Side Panel (+10 more)

### Community 30 - "Posting Details Fetcher"
Cohesion: 0.19
Nodes (16): fetch_posting(), fill_descriptions(), linkedin_job_id(), _linkedin_reader(), parse_posting(), Posting, Fill in missing job descriptions, so the experience rules can be checked.  Lin, Description and closed flag from a LinkedIn job page, parsed with JobSpy's own h (+8 more)

### Community 31 - "Dashboard Tabs"
Cohesion: 0.19
Nodes (17): Counter, bar(), detail_panel(), insights_tab(), jobs_tab(), load_jobs(), main(), pipeline_tab() (+9 more)

### Community 32 - "UI Components and Theme"
Cohesion: 0.14
Nodes (11): brand_header(), current_scheme(), inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma c, dark' or 'light', as the browser actually renders it., Sidebar masthead: brand name with the sparkles mark (Figma 7:2430) and the kit b, Call once at the top of the page, after st.set_page_config. (+3 more)

### Community 33 - "vLLM and Docker Overlays"
Cohesion: 0.23
Nodes (15): config.docker.yaml (vllm service + host LM Studio for agent), config.docker.lmstudio.yaml (LM Studio via host.docker.internal), llm config (LM Studio Qwen 27B), config.vllm.yaml overlay (local vLLM scorer), qwen3-local served model (Qwen3-14B AWQ on vLLM), docker-compose.yml (app demo container), docker-compose.vllm.yml (vllm GPU service overlay), vllm service (vllm/vllm-openai v0.31.0) (+7 more)

### Community 34 - "Company Sync Script"
Cohesion: 0.21
Nodes (15): add_to_yaml(), boards_in(), candidates(), download_techmap(), existing(), israel_jobs(), main(), Add Israeli companies' job boards to companies.yaml from the open Israeli Tech M (+7 more)

### Community 35 - "Project Docs and Conventions"
Cohesion: 0.15
Nodes (14): Project conventions (collectors never raise, optional LLM, user fields protected), Job Hunter Agent, Project skills (.claude/skills), Multi-user model (owner + users/<id>), cv/README (put CV here, newest wins), Collectors (JobSpy, ATS boards, techmap, getro, remote boards, SerpAPI), Decision: fixed graph over ReAct for batch pipeline, Several users on one PC (auto_from_cv) (+6 more)

### Community 36 - "Collector Registry and SerpAPI"
Cohesion: 0.21
Nodes (11): collect_serpapi(), parse_serpapi(), posted_at_to_iso(), Google Jobs through SerpAPI (optional; skipped without SERPAPI_API_KEY).  Goog, Google's relative `posted_at` ("2 days ago", "30+ days ago", "Just posted") -> ', Any, CollectorResult, datetime (+3 more)

### Community 37 - "Config and Filter Settings"
Cohesion: 0.17
Nodes (13): filters config (experience limit, role keywords), matching config (llm_scoring false, llm_top_n), search config (queries, employers), sources config, Experience limit (junior_reason), LLM score (JobMatch structured output), Pre-score (TF-IDF + skill overlap), Three-stage scoring (rule filter, pre-score, LLM score) (+5 more)

### Community 38 - "Scoring and Status Concepts"
Cohesion: 0.20
Nodes (15): Jobs table with editable status, job-matching skill, Candidate choices feedback block, LLM required_years backstop, matcher.llm_score (JobMatch), Location filter (is_israel / remote_ok), Filter -> prescore -> LLM score, STATUSES constant (+7 more)

### Community 39 - "Handoff Tests"
Cohesion: 0.14
Nodes (3): A user with a CV and one scored job, all inside the temp folder., test_brief_for_heuristic_job_and_unknown_id(), user()

### Community 40 - "CV Tailoring Agent"
Cohesion: 0.27
Nodes (13): cv-tailoring skill, Tailoring kit outputs (changes.md, gaps.md, cover letter), No-fabrication rule, CV Tailoring Agent graph (Phase 8), verify node (fact-check loop), Master CV schema (cv_master.yaml), Owner CV rules, Experience bank and NOT list (+5 more)

### Community 41 - "Job Filters and Experience"
Cohesion: 0.31
Nodes (12): date, age_ok(), drop_reason(), is_israel(), location_ok(), Stage 1: cheap rule filters (location, role, seniority, age) with per-reason dro, Whole-word match (so 'lead' does not hit 'leading', 'sr ' does not hit 'usr ')., region_pattern() (+4 more)

### Community 42 - "Getro Collector"
Cohesion: 0.27
Nodes (10): get_json(), get_session(), get_text(), Shared HTTP session, text/date helpers and the collector result type., One session: User-Agent, retry 3x with backoff on 429/5xx., Any, main(), Record trimmed raw API responses into tests/fixtures/ (run manually when an API (+2 more)

### Community 43 - "Tailoring and Handoff Docs"
Cohesion: 0.17
Nodes (11): tailoring config, Claude handoff (brief.md, subscription env), CV Tailoring Agent (planned Phase 8), Headless auto-tailor (claude -p), Per-phase acceptance checks, Phase 8: CV Tailoring Agent (not started), Phase 9: Auto-tailor on the subscription, USER_GUIDE.he.md (Hebrew user guide) (+3 more)

### Community 44 - "Sidebar Preferences"
Cohesion: 0.17
Nodes (12): default_goal(), experience_toggle(), init_prefs(), pref_defaults(), Two short lines; every number is isolated with <bdi> so Hebrew and digits keep t, Seed widget state from the URL when a widget has no state yet (widgets then take, Write non-default settings to the URL; defaults are left out to keep it short., The "experience limit" view toggle, worded for this user's limit; none when ther (+4 more)

### Community 45 - "Dashboard Design System"
Cohesion: 0.27
Nodes (12): dashboard-design skill, Color has meaning rule, Render-and-compare loop (compare.py), Job Hunter Dashboard Figma file, Three-layer design architecture (config.toml / tokens+css / components), Figma map, Night dark theme (8:27), Sea light theme (2:30) (+4 more)

### Community 46 - "Desktop Notifications"
Cohesion: 0.27
Nodes (10): notify_strong_matches(), Any, Optional desktop notification after a run when new strong matches were found (co, Fire-and-forget balloon notification (no extra modules needed)., Returns how many strong matches were announced (0 when disabled or none)., strong_matches(), windows_balloon(), test_announces_best_match_and_count() (+2 more)

### Community 47 - "Agent Loop Tools"
Cohesion: 0.26
Nodes (11): line(), main(), outcome(), picked_by(), Path, How good are the smart agent's picks, judged by what you did with them in the da, agent (saved by the agent, scored or not) / regular (LLM-scored) / heuristic (no, {"jobs", "pursued", "dismissed", "open", "judged", "precision" (None when nothin (+3 more)

### Community 48 - "Plugin Guard Rules"
Cohesion: 0.27
Nodes (5): BASH_RULES, checkBash(), checkFile(), isPython(), Verdict

### Community 49 - "Job Filters and Experience"
Cohesion: 0.25
Nodes (11): contains_any(), excluded_title(), _norm_title(), Any, An `exclude_keywords` title ("Sales", "Technician") that no `exclude_exceptions`, A computer-science role: a CS title, or a description asking for a CS / engineer, (padded lower-case title, same with punctuation turned into spaces)., Substring match on the padded title, so keywords like ' ai ' and 'ml ' work. (+3 more)

### Community 50 - "Agent Loop Tools"
Cohesion: 0.27
Nodes (9): NoArgs, ReadArgs, SaveArgs, SearchArgs, BaseModel, Any, Counter, JobMatch (+1 more)

### Community 51 - "Headless Auto-Tailor"
Cohesion: 0.36
Nodes (10): apply skill (/apply <job-id>), Unattended /apply mode, auto-tailor skill, auto_tailor_node, Never pass --bare, handoff.run_headless, subscription_env() child environment, tailoring.auto_* config (+2 more)

### Community 52 - "UI Component Helpers"
Cohesion: 0.20
Nodes (5): inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma com, Call once at the top of the page, after st.set_page_config., items in reading order (right → left in RTL): [("משרות מתאימות", 12), ...]

### Community 53 - "Board Check ATS"
Cohesion: 0.24
Nodes (4): check(), label(), main(), Validate companies.yaml: which ATS slugs are alive and how many Israel jobs each

### Community 54 - "Job Sources Skill"
Cohesion: 0.29
Nodes (10): job-sources skill, Collector contract (CollectorResult, never raise), collectors/details.py description + closed-job fetch, JobSpy collector, RateLimitWatch (LinkedIn 429), Shared requests.Session (base.get_session), Job source endpoints and field mappings, Comeet careers API (+2 more)

### Community 55 - "Getro Collector"
Cohesion: 0.33
Nodes (8): collect_getro(), fetch_board(), parse_getro(), Venture-capital portfolio job boards on Getro (e.g. Israel VC Forum: ~880 portfo, search_page(), Any, CollectorResult, Job

### Community 56 - "Agent Memory and Precision"
Cohesion: 0.22
Nodes (8): agent config (goal, budgets, role_groups), Agent memory across runs, Role groups coverage enforcement, Search agent loop (ReAct, guardrails in code), Stopping a run (stop.flag), PR #6 smart agent rework (7 changes), Robustness fix 1f86c9e (fatal_llm_error, no re-saves, 429), Agent loop (--agent)

### Community 57 - "Cross-source Dedupe"
Cohesion: 0.28
Nodes (8): dedupe_batch(), is_new(), Job, Dedupe: the same posting (same id) or the same role on several boards (same comp, Lower is better: company boards (full descriptions) beat JobSpy beat remote boar, Drop repeated ids; for the same company|title keep the best source (board > jobs, Not stored yet, neither as this posting nor as the same role from another board., source_priority()

### Community 58 - "Run Lock and Stop"
Cohesion: 0.36
Nodes (8): clear_stale_stop(), clear_stop(), Path, Graceful stop: the dashboard writes <run dir>/stop.flag; a running search checks, At run start: drop a request left over from an earlier run, but keep a fresh one, request_stop(), stop_path(), stop_requested()

### Community 59 - "Run Controls"
Cohesion: 0.36
Nodes (8): _health_url(), is_running(), local_llm_down(), True when the agent's local model server (LM Studio / vLLM base_url) does not an, Live log while a run is going; only this fragment polls, the controls stay still, run_active(), run_controls(), run_status()

### Community 60 - "Light Dashboard Screenshot"
Cohesion: 0.32
Nodes (8): Dashboard Screenshot (Light Theme), Hebrew RTL UI with Sea (light purple) theme, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, note, sent checkbox, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Minimum Match Score Slider, Sidebar: Run Search Button, Smart Agent Toggle, Filters, Dashboard Tabs (Jobs, Pipeline, Insights, Sources, Profile)

### Community 61 - "Filters and Guardrails Docs"
Cohesion: 0.38
Nodes (7): collect_company_boards(), entry_label(), _one_company(), How a companies.yaml entry is named in errors: the slug, or the Workday tenant., Fetch every company in companies.yaml. `limit` caps jobs kept per company., Any, CollectorResult

### Community 62 - "Company Boards Config"
Cohesion: 0.29
Nodes (7): companies.yaml (ATS company boards), ATS types: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Comeet, JOB_SOURCES_RESEARCH.md (additional job sources), Israeli job boards (Drushim, AllJobs, JobMaster), Microsoft Careers / eightfold ATS type, Goozali Telegram junior channels, Jobicy remote API

### Community 63 - "Render Compare Tool"
Cohesion: 0.33
Nodes (6): Run lock (runlock.py, run.lock), handoff.py per-job brief, job-dashboard skill, Prepare application with Claude button, Per-session user/DB selection, Test isolation via env vars (JOBHUNTER_DB/RUN_DIR/USERS_DIR)

### Community 64 - "CV Sent Controls"
Cohesion: 0.60
Nodes (5): Path, main(), Render the running dashboard and put it next to the Figma reference.  Usage (fro, render(), side_by_side()

### Community 65 - "User Switching"
Cohesion: 0.33
Nodes (5): LastRun, Phase, PluginState, Progress, Tests

### Community 66 - "Test Conftest"
Cohesion: 0.40
Nodes (5): on_add_user(), owner_label(), Start the other user's view clean: filters, table edits and run state belong to, switch_user(), user_picker()

### Community 67 - "Job Filters and Experience"
Cohesion: 0.50
Nodes (4): main(), Path, Which stored jobs ask for more experience than config.yaml allows, and how each, report()

### Community 69 - "Figma Reference App"
Cohesion: 0.50
Nodes (4): _fake_serpapi(), Record the queries sent to SerpAPI; answer each with the sample fixture., test_serpapi_falls_back_to_search_queries(), test_serpapi_uses_its_own_query_list()

## Knowledge Gaps
- **80 isolated node(s):** `BASH_RULES`, `Verdict`, `RUN`, `EMPTY`, `progress` (+75 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Job` connect `Collector Registry and SerpAPI` to `Handoff Tests`, `Named Users`, `Getro Collector`, `Collector Tests`, `Remote Job Boards`, `CV Personalization Tests`, `Getro Collector`, `ATS Board Collectors`, `Collector Registry and SerpAPI`, `JobSpy Collector`, `Filters and Guardrails Docs`, `Posting Details Fetcher`, `Cross-source Dedupe`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `Dashboard Dark Mode Screenshot` connect `Figma Light Screens` to `Dashboard User Forms`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `Job` (e.g. with `CollectorResult` and `Posting`) actually correct?**
  _`Job` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `CollectorResult` (e.g. with `Job` and `RateLimitWatch`) actually correct?**
  _`CollectorResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `AgentContext` (e.g. with `AgentUnavailable` and `LoopState`) actually correct?**
  _`AgentContext` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Visual prototype of Figma frame 2:30 'Dashboard / Jobs' with static sample data.`, `Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma com`, `Call once at the top of the page, after st.set_page_config.` to the rest of the system?**
  _299 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `CV Profile and Handoff` be split into smaller, more focused modules?**
  _Cohesion score 0.06861239119303636 - nodes in this community are weakly interconnected._