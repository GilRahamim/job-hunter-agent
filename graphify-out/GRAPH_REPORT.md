# Graph Report - .  (2026-10-21)

## Corpus Check
- 131 files · ~141,142 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1242 nodes · 2913 edges · 72 communities (69 shown, 3 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 240 edges (avg confidence: 0.61)
- Token cost: 748,324 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Users and CV Profile|Users and CV Profile]]
- [[_COMMUNITY_Job Filters|Job Filters]]
- [[_COMMUNITY_Agent Loop Graph|Agent Loop Graph]]
- [[_COMMUNITY_Project Conventions and Config|Project Conventions and Config]]
- [[_COMMUNITY_Agent Loop Tests|Agent Loop Tests]]
- [[_COMMUNITY_SQLite Storage|SQLite Storage]]
- [[_COMMUNITY_ATS Board Collectors|ATS Board Collectors]]
- [[_COMMUNITY_Agent Loop Tools|Agent Loop Tools]]
- [[_COMMUNITY_TechMap Getro SerpAPI Sources|TechMap Getro SerpAPI Sources]]
- [[_COMMUNITY_Collector Registry|Collector Registry]]
- [[_COMMUNITY_LLM Provider|LLM Provider]]
- [[_COMMUNITY_Run Lock and Stop|Run Lock and Stop]]
- [[_COMMUNITY_Named Users|Named Users]]
- [[_COMMUNITY_Collector Tests|Collector Tests]]
- [[_COMMUNITY_Dashboard Tests|Dashboard Tests]]
- [[_COMMUNITY_Remote Job Boards|Remote Job Boards]]
- [[_COMMUNITY_Search Pipeline Nodes|Search Pipeline Nodes]]
- [[_COMMUNITY_Fixture-based Source Tests|Fixture-based Source Tests]]
- [[_COMMUNITY_Agent Pipeline Skill|Agent Pipeline Skill]]
- [[_COMMUNITY_Plugin Panel Parsing|Plugin Panel Parsing]]
- [[_COMMUNITY_Matcher Scoring|Matcher Scoring]]
- [[_COMMUNITY_Matcher Tests|Matcher Tests]]
- [[_COMMUNITY_Dashboard User Forms|Dashboard User Forms]]
- [[_COMMUNITY_Posting Details Fetcher|Posting Details Fetcher]]
- [[_COMMUNITY_JobSpy Collector|JobSpy Collector]]
- [[_COMMUNITY_CV Personalization|CV Personalization]]
- [[_COMMUNITY_DB Tests|DB Tests]]
- [[_COMMUNITY_Config Loading|Config Loading]]
- [[_COMMUNITY_Company Sync Script|Company Sync Script]]
- [[_COMMUNITY_UI Components and Theme|UI Components and Theme]]
- [[_COMMUNITY_Dashboard Tabs|Dashboard Tabs]]
- [[_COMMUNITY_Scoring and Status Concepts|Scoring and Status Concepts]]
- [[_COMMUNITY_Agent Tool Schemas|Agent Tool Schemas]]
- [[_COMMUNITY_Handoff Tests|Handoff Tests]]
- [[_COMMUNITY_CV Tailoring Rules|CV Tailoring Rules]]
- [[_COMMUNITY_Shared HTTP Session|Shared HTTP Session]]
- [[_COMMUNITY_Dashboard Design System|Dashboard Design System]]
- [[_COMMUNITY_Desktop Notifications|Desktop Notifications]]
- [[_COMMUNITY_Figma Jobs Screen|Figma Jobs Screen]]
- [[_COMMUNITY_Agent Precision Report|Agent Precision Report]]
- [[_COMMUNITY_Plugin Guard Rules|Plugin Guard Rules]]
- [[_COMMUNITY_Getro and Job Model|Getro and Job Model]]
- [[_COMMUNITY_Headless Auto-Tailor|Headless Auto-Tailor]]
- [[_COMMUNITY_UI Component Helpers|UI Component Helpers]]
- [[_COMMUNITY_Board Check Script|Board Check Script]]
- [[_COMMUNITY_Job Sources Skill|Job Sources Skill]]
- [[_COMMUNITY_Run Directory Paths|Run Directory Paths]]
- [[_COMMUNITY_Dark Render Screenshot|Dark Render Screenshot]]
- [[_COMMUNITY_Light Render Screenshot|Light Render Screenshot]]
- [[_COMMUNITY_Job Detail Panel|Job Detail Panel]]
- [[_COMMUNITY_Dark Dashboard Screenshot|Dark Dashboard Screenshot]]
- [[_COMMUNITY_Cross-source Dedupe|Cross-source Dedupe]]
- [[_COMMUNITY_Figma Night Split Screen|Figma Night Split Screen]]
- [[_COMMUNITY_SerpAPI Parser|SerpAPI Parser]]
- [[_COMMUNITY_Sidebar Preferences|Sidebar Preferences]]
- [[_COMMUNITY_Run Controls|Run Controls]]
- [[_COMMUNITY_Light Dashboard Screenshot|Light Dashboard Screenshot]]
- [[_COMMUNITY_Figma Editorial Screen|Figma Editorial Screen]]
- [[_COMMUNITY_Handoff and Isolation|Handoff and Isolation]]
- [[_COMMUNITY_Render Compare Tool|Render Compare Tool]]
- [[_COMMUNITY_Company Board Fetch|Company Board Fetch]]
- [[_COMMUNITY_Plugin State Types|Plugin State Types]]
- [[_COMMUNITY_User Switching|User Switching]]
- [[_COMMUNITY_Test Conftest|Test Conftest]]
- [[_COMMUNITY_SerpAPI Tests|SerpAPI Tests]]
- [[_COMMUNITY_Figma Reference App|Figma Reference App]]
- [[_COMMUNITY_Sparkles Icon|Sparkles Icon]]

## God Nodes (most connected - your core abstractions)
1. `Job` - 143 edges
2. `CollectorResult` - 60 edges
3. `CandidateProfile` - 58 edges
4. `load_config()` - 51 edges
5. `AgentContext` - 34 edges
6. `ScriptedModel` - 32 edges
7. `JobMatch` - 31 edges
8. `clean()` - 28 edges
9. `to_iso()` - 26 edges
10. `connect()` - 25 edges

## Surprising Connections (you probably didn't know these)
- `datetime` --uses--> `CandidateProfile`  [INFERRED]
  dashboard.py → jobhunter/models.py
- `datetime` --uses--> `UserError`  [INFERRED]
  dashboard.py → jobhunter/users.py
- `DataFrame` --uses--> `CandidateProfile`  [INFERRED]
  dashboard.py → jobhunter/models.py
- `DataFrame` --uses--> `UserError`  [INFERRED]
  dashboard.py → jobhunter/users.py
- `Figure` --uses--> `CandidateProfile`  [INFERRED]
  dashboard.py → jobhunter/models.py

## Import Cycles
- 1-file cycle: `dashboard.py -> dashboard.py`
- 1-file cycle: `jobhunter/collectors/serpapi.py -> jobhunter/collectors/serpapi.py`

## Hyperedges (group relationships)
- **Search pipeline: collect -> filter -> prescore -> LLM score -> save** — job_sources_skill_collector_contract, job_matching_skill_location_filter, job_matching_skill_prescore, job_matching_skill_llm_score, job_storage_skill_upsert_jobs, agent_pipeline_skill_langgraph_stategraph [EXTRACTED 1.00]
- **No-fabrication enforcement across tailoring paths** — cv_tailoring_skill_no_fabrication_rule, cv_tailoring_skill_verify_node, references_prompts_rewrite_prompt, references_owner_cv_rules, apply_skill, apply_skill_handoff_brief [INFERRED 0.85]
- **Headless tailoring on the Claude subscription** — auto_tailor_skill_auto_tailor_node, auto_tailor_skill_run_headless, auto_tailor_skill_subscription_env, auto_tailor_skill_never_bare, references_claude_cli_headless_auth_precedence [EXTRACTED 1.00]
- **Filter -> pre-score -> LLM score flow** — config_filters, docs_architecture_prescore_formula, jobhunter_skills_vocab, config_matching, config_llm, docs_architecture_three_stage_scoring [INFERRED 0.85]
- **Tailoring on the Claude subscription** — docs_architecture_claude_handoff, docs_architecture_headless_auto_tailor, docs_architecture_subscription_env, config_tailoring, docs_implementation_plan_phase9, claude_no_fabrication_rule [INFERRED 0.85]
- **Agent loop controls (guardrails, memory, role groups, history trimming)** — docs_architecture_search_agent_loop, docs_architecture_agent_guardrails, docs_architecture_agent_memory, docs_architecture_compact_history, config_agent_role_groups, config_agent [INFERRED 0.85]
- **Filter -> table -> detail job review flow** — screens_figma_2_30_dashboard_jobs_sidebar_filters, screens_figma_2_30_dashboard_jobs_jobs_table, screens_figma_2_30_dashboard_jobs_job_detail_panel, screens_figma_2_30_dashboard_jobs_skill_chips [INFERRED 0.85]
- **Dark Jobs screen composition: tabs, KPI cards, table, detail panel** — screens_figma_8_27_dark_moody_split_hebrew_rtl_tabs, screens_figma_8_27_dark_moody_split_kpi_cards, screens_figma_8_27_dark_moody_split_jobs_table, screens_figma_8_27_dark_moody_split_job_detail_panel [EXTRACTED 1.00]
- **Jobs tab layout: nav, KPIs, table, detail panel** — screens_figma_8_665_muted_editorial_rtl_tab_nav, screens_figma_8_665_muted_editorial_kpi_row, screens_figma_8_665_muted_editorial_jobs_table, screens_figma_8_665_muted_editorial_job_detail_panel [EXTRACTED 1.00]
- **Jobs screen composition: sidebar filters, KPI row, table, detail panel** — screens_verified_render_dark_filter_sidebar, screens_verified_render_dark_kpi_cards, screens_verified_render_dark_jobs_table, screens_verified_render_dark_job_detail_panel [EXTRACTED 1.00]
- **Jobs tab screen composition (filters -> KPIs -> table -> detail)** — screens_verified_render_light_sidebar_filters, screens_verified_render_light_kpi_cards, screens_verified_render_light_jobs_table, screens_verified_render_light_job_detail_panel [INFERRED 0.85]
- **Dashboard main view: sidebar controls + KPI cards + jobs table** — images_dashboard_dark_sidebar_run_controls, images_dashboard_dark_sidebar_filters, images_dashboard_dark_kpi_cards, images_dashboard_dark_jobs_table, images_dashboard_dark_tabs_nav [EXTRACTED 1.00]
- **Application tracking view: KPIs, filters and jobs table** — images_dashboard_light_kpi_cards, images_dashboard_light_jobs_table, images_dashboard_light_sidebar, images_dashboard_light_min_score_slider [INFERRED 0.85]

## Communities (72 total, 3 thin omitted)

### Community 0 - "Users and CV Profile"
Cohesion: 0.06
Nodes (72): active_user(), The user this process works for; "" is the owner. The dashboard passes users exp, apply_overrides(), CVError, extract_heuristic(), extract_with_llm(), file_hash(), find_cv() (+64 more)

### Community 1 - "Job Filters"
Cohesion: 0.07
Nodes (62): date, age_ok(), contains_any(), drop_reason(), excluded_title(), experience_ok(), filter_jobs(), is_israel() (+54 more)

### Community 2 - "Agent Loop Graph"
Cohesion: 0.06
Nodes (55): agent_llm_config(), AgentUnavailable, build_graph(), compact_history(), experience_limit(), initial_messages(), Tool-using agent loop (ReAct style): the model picks the next tool until it reac, One line per group; with history, each line says what the group gave in recent r (+47 more)

### Community 3 - "Project Conventions and Config"
Cohesion: 0.05
Nodes (58): CLAUDE.md project instructions, Collector contract: return list[Job], never raise, JOBHUNTER_USER env var / --user path resolution, No-fabrication rule (only facts from cv_master.yaml), LLM is optional (provider none -> heuristic scores), Never overwrite user-owned fields (status, notes), companies.yaml (ATS company boards), ATS types: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Comeet (+50 more)

### Community 4 - "Agent Loop Tests"
Cohesion: 0.11
Nodes (37): call(), calls(), env(), Replays a fixed list of replies; records the messages it was shown. As the score, One model turn with several tool calls: calls(("read_posting", {...}), ("read_po, A context where `job` was found and read in an earlier tool turn., read_ctx(), ScriptedModel (+29 more)

### Community 5 - "SQLite Storage"
Cohesion: 0.12
Nodes (41): Connection, _add_column(), all_jobs(), backfill_required_years(), connect(), db_path(), _decode(), _dumps() (+33 more)

### Community 6 - "ATS Board Collectors"
Cohesion: 0.11
Nodes (32): _company_name(), fetch_ashby(), fetch_comeet(), fetch_greenhouse(), fetch_lever(), fetch_smartrecruiters(), fetch_workday(), israel_facets() (+24 more)

### Community 7 - "Agent Loop Tools"
Cohesion: 0.12
Nodes (33): _add_candidate(), AgentContext, coverage_note(), _fetch(), get_profile(), group_cap(), is_free(), jobspy_sites() (+25 more)

### Community 8 - "TechMap Getro SerpAPI Sources"
Cohesion: 0.13
Nodes (27): CollectorResult, collect_getro(), collect_serpapi(), collect_techmap(), parse_techmap(), Israeli Tech Map daily job lists (https://github.com/mluggy/techmap, ODbL v1.0)., Any, CollectorResult (+19 more)

### Community 9 - "Collector Registry"
Cohesion: 0.09
Nodes (18): collect_all(), _load(), Collector registry: {name: fn} and collect_all()., Run enabled sources in parallel (or just `only`). Returns (results, health recor, _run_one(), Any, CollectorResult, test_collect_all_respects_enabled_flags_and_rejects_unknown() (+10 more)

### Community 10 - "LLM Provider"
Cohesion: 0.12
Nodes (18): get_llm(), _has_key(), llm_available(), Any, Provider-agnostic chat model. Returns None when the LLM is disabled or has no ke, True when get_llm() would return a model (provider set and its key present), wit, A LangChain chat model, or None -> callers fall back to heuristics., FakeLLM (+10 more)

### Community 11 - "Run Lock and Stop"
Cohesion: 0.14
Nodes (20): force_stop(), Last resort when a graceful stop takes too long: kill the run (its results are l, lock_path(), pid_alive(), Path, One run at a time: <run dir>/run.lock holds the PID of the running search (pipel, PID of the run holding the lock, or None when no live run holds it., Context manager around run.lock. Clears a stale stop request on entry and the st (+12 more)

### Community 12 - "Named Users"
Cohesion: 0.13
Nodes (24): create_user(), display_name(), list_users(), _new_id(), _owner_cv_dir(), Path, Named users (e.g. a partner who wants their own search): created from an uploade, Bad input from the add-user form; the message is shown to the person (Hebrew). (+16 more)

### Community 13 - "Collector Tests"
Cohesion: 0.09
Nodes (12): Job, test_a_429_on_the_last_search_is_still_reported(), test_company_boards_accept_workday_and_comeet_entries(), test_fill_descriptions_only_reads_jobs_without_one(), test_fill_descriptions_reports_closed_jobs(), test_fill_descriptions_stops_at_a_429(), test_html_to_text_unescapes_greenhouse_style(), test_jobspy_partial_miss_is_a_warning_not_an_error() (+4 more)

### Community 14 - "Dashboard Tests"
Cohesion: 0.15
Nodes (21): _app(), _launch(), _Ok, A reload (e.g. the theme switch) keeps filters and the run mode., The owner with one job and a user created from a CV with two jobs of their own., test_agent_mode_blocks_run_when_local_model_server_is_down(), test_agent_mode_runs_agent_with_chosen_goal(), test_bad_url_values_fall_back_to_valid_ones() (+13 more)

### Community 15 - "Remote Job Boards"
Cohesion: 0.22
Nodes (23): html_to_text(), HTML (or HTML-escaped HTML, as Greenhouse sends) -> plain text., _arbeitnow(), _collect(), collect_arbeitnow(), collect_himalayas(), collect_remoteok(), collect_remotive() (+15 more)

### Community 16 - "Search Pipeline Nodes"
Cohesion: 0.16
Nodes (22): LoopState, after_prescore(), build_graph(), collect_node(), _db(), dedupe_node(), filter_node(), llm_score_node() (+14 more)

### Community 17 - "Fixture-based Source Tests"
Cohesion: 0.14
Nodes (22): fixture(), assert_clean(), test_arbeitnow_keeps_remote_only(), test_ashby(), test_comeet(), test_comeet_reads_the_token_from_the_careers_page(), test_getro_board(), test_getro_pages_until_the_count() (+14 more)

### Community 18 - "Agent Pipeline Skill"
Cohesion: 0.13
Nodes (20): agent-pipeline skill, Conditional LLM edge (llm_enabled), LangGraph search pipeline graph, No built-in scheduling, notify node (strong matches), PipelineState, run_agent.py CLI flags, cv-profile skill (+12 more)

### Community 19 - "Plugin Panel Parsing"
Cohesion: 0.19
Nodes (15): isAgentRun(), isPytest(), parsePlan(), parsePytest(), readLastRun(), readPhaseNumber(), shortTime(), toPhase() (+7 more)

### Community 20 - "Matcher Scoring"
Cohesion: 0.18
Nodes (19): build_messages(), fatal_llm_error(), llm_score(), preferences_text(), prescore(), Any, CandidateProfile, Job (+11 more)

### Community 21 - "Matcher Tests"
Cohesion: 0.14
Nodes (10): cfg(), FakeLLM, job(), Stand-in for llm.with_structured_output(JobMatch); scorer sees the prompt text., test_choices_reach_the_prompt_only_when_the_user_marked_jobs(), test_failure_returns_none_and_falls_back_to_prescore(), test_llm_score_preserves_order_and_parses(), test_prescore_years_gap_penalty() (+2 more)

### Community 22 - "Dashboard User Forms"
Cohesion: 0.14
Nodes (15): add_user_form(), cv_upload_form(), default_goal(), on_cv_upload(), on_stop_toggle(), pref_defaults(), profile_tab(), profile_view() (+7 more)

### Community 23 - "Posting Details Fetcher"
Cohesion: 0.19
Nodes (16): fetch_posting(), fill_descriptions(), linkedin_job_id(), _linkedin_reader(), parse_posting(), Posting, Fill in missing job descriptions, so the experience rules can be checked.  Lin, Description and closed flag from a LinkedIn job page, parsed with JobSpy's own h (+8 more)

### Community 24 - "JobSpy Collector"
Cohesion: 0.18
Nodes (12): collect_jobspy(), employer_queries(), frame_to_jobs(), _quoted(), RateLimitWatch, LinkedIn / Indeed / Glassdoor / Google Jobs through the python-jobspy library., Notices "status code 429" in JobSpy's LinkedIn log, so a run stops asking Linked, Convert a JobSpy DataFrame (or a CSV loaded with pandas) to Jobs. (+4 more)

### Community 25 - "CV Personalization"
Cohesion: 0.20
Nodes (15): experience_limit(), _not_in(), personalize(), Any, CandidateProfile, `auto_from_cv: true` (set for users created from the dashboard): search settings, Role keywords from job titles, in the form filters.contains_any expects     ("D, Keywords that do not occur in any of the titles (a marketer must not drop "marke (+7 more)

### Community 26 - "DB Tests"
Cohesion: 0.17
Nodes (12): get(), make_row(), test_agent_report_compares_picks_with_what_the_user_did(), test_backfill_required_years(), test_env_override(), test_existing_ids_and_keys(), test_experience_report_names_how_each_job_got_in(), test_first_seen_kept_last_seen_refreshed() (+4 more)

### Community 27 - "Config Loading"
Cohesion: 0.20
Nodes (14): main(), python -m jobhunter.collectors --source ats --limit 5, The config this user's runs use: auto_from_cv users get the filters derived from, search_config(), deep_merge(), load_companies(), load_config(), load_env() (+6 more)

### Community 28 - "Company Sync Script"
Cohesion: 0.21
Nodes (15): add_to_yaml(), boards_in(), candidates(), download_techmap(), existing(), israel_jobs(), main(), Add Israeli companies' job boards to companies.yaml from the open Israeli Tech M (+7 more)

### Community 29 - "UI Components and Theme"
Cohesion: 0.15
Nodes (11): brand_header(), current_scheme(), inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma c, dark' or 'light', as the browser actually renders it., Sidebar masthead: brand name with the sparkles mark (Figma 7:2430) and the kit b, Call once at the top of the page, after st.set_page_config. (+3 more)

### Community 30 - "Dashboard Tabs"
Cohesion: 0.21
Nodes (15): bar(), init_prefs(), insights_tab(), jobs_tab(), load_jobs(), main(), pipeline_tab(), Seed widget state from the URL when a widget has no state yet (widgets then take (+7 more)

### Community 31 - "Scoring and Status Concepts"
Cohesion: 0.20
Nodes (15): Jobs table with editable status, job-matching skill, Candidate choices feedback block, LLM required_years backstop, matcher.llm_score (JobMatch), Location filter (is_israel / remote_ok), Filter -> prescore -> LLM score, STATUSES constant (+7 more)

### Community 32 - "Agent Tool Schemas"
Cohesion: 0.30
Nodes (13): _new_and_filtered(), NoArgs, ReadArgs, SaveArgs, SearchArgs, BaseModel, Any, Counter (+5 more)

### Community 33 - "Handoff Tests"
Cohesion: 0.14
Nodes (3): A user with a CV and one scored job, all inside the temp folder., test_brief_for_heuristic_job_and_unknown_id(), user()

### Community 34 - "CV Tailoring Rules"
Cohesion: 0.27
Nodes (13): cv-tailoring skill, Tailoring kit outputs (changes.md, gaps.md, cover letter), No-fabrication rule, CV Tailoring Agent graph (Phase 8), verify node (fact-check loop), Master CV schema (cv_master.yaml), Owner CV rules, Experience bank and NOT list (+5 more)

### Community 35 - "Shared HTTP Session"
Cohesion: 0.27
Nodes (10): get_json(), get_session(), get_text(), Shared HTTP session, text/date helpers and the collector result type., One session: User-Agent, retry 3x with backoff on 429/5xx., Any, main(), Record trimmed raw API responses into tests/fixtures/ (run manually when an API (+2 more)

### Community 36 - "Dashboard Design System"
Cohesion: 0.27
Nodes (12): dashboard-design skill, Color has meaning rule, Render-and-compare loop (compare.py), Job Hunter Dashboard Figma file, Three-layer design architecture (config.toml / tokens+css / components), Figma map, Night dark theme (8:27), Sea light theme (2:30) (+4 more)

### Community 37 - "Desktop Notifications"
Cohesion: 0.27
Nodes (10): notify_strong_matches(), Any, Optional desktop notification after a run when new strong matches were found (co, Fire-and-forget balloon notification (no extra modules needed)., Returns how many strong matches were announced (0 when disabled or none)., strong_matches(), windows_balloon(), test_announces_best_match_and_count() (+2 more)

### Community 38 - "Figma Jobs Screen"
Cohesion: 0.23
Nodes (12): Figma 2:30 Dashboard Jobs Screen, Job Detail Panel (score badge, title, meta, notes, save / open job), Jobs Table (score bar, role, company, location, source, days, assessment, status, link), KPI Cards (matching jobs, new today, strong match 75+, applied), Preliminary (heuristic, no-LLM) Score Label, RTL Hebrew Layout (sidebar on right), Find New Jobs Button + Last Run Summary, Sea Light Theme (teal accent, soft gray surfaces) (+4 more)

### Community 39 - "Agent Precision Report"
Cohesion: 0.26
Nodes (11): line(), main(), outcome(), picked_by(), Path, How good are the smart agent's picks, judged by what you did with them in the da, agent / regular (LLM-scored) / heuristic (no LLM score; includes jobs the agent, {"jobs", "pursued", "dismissed", "open", "judged", "precision" (None when nothin (+3 more)

### Community 40 - "Plugin Guard Rules"
Cohesion: 0.27
Nodes (5): BASH_RULES, checkBash(), checkFile(), isPython(), Verdict

### Community 41 - "Getro and Job Model"
Cohesion: 0.24
Nodes (8): fetch_board(), parse_getro(), Venture-capital portfolio job boards on Getro (e.g. Israel VC Forum: ~880 portfo, search_page(), Job, _clean_url(), Core data models: Job (collected), CandidateProfile (from CV), JobMatch (from LL, Lower-case and drop tracking params (utm_*, refId, trackingId, trk).

### Community 42 - "Headless Auto-Tailor"
Cohesion: 0.36
Nodes (10): apply skill (/apply <job-id>), Unattended /apply mode, auto-tailor skill, auto_tailor_node, Never pass --bare, handoff.run_headless, subscription_env() child environment, tailoring.auto_* config (+2 more)

### Community 43 - "UI Component Helpers"
Cohesion: 0.20
Nodes (5): inject_theme(), kpi_row(), Reusable dashboard pieces matching the Figma components (frame 2:16).  Figma com, Call once at the top of the page, after st.set_page_config., items in reading order (right → left in RTL): [("משרות מתאימות", 12), ...]

### Community 44 - "Board Check Script"
Cohesion: 0.24
Nodes (4): check(), label(), main(), Validate companies.yaml: which ATS slugs are alive and how many Israel jobs each

### Community 45 - "Job Sources Skill"
Cohesion: 0.29
Nodes (10): job-sources skill, Collector contract (CollectorResult, never raise), collectors/details.py description + closed-job fetch, JobSpy collector, RateLimitWatch (LinkedIn 429), Shared requests.Session (base.get_session), Job source endpoints and field mappings, Comeet careers API (+2 more)

### Community 46 - "Run Directory Paths"
Cohesion: 0.33
Nodes (10): data_dir(), Path, Parent folder of the named users. JOBHUNTER_USERS_DIR overrides it (tests)., Base folder of a user: the repo itself for the owner, users/<name>/ otherwise., Where run.lock, stop.flag and run logs live. For the owner JOBHUNTER_RUN_DIR ove, run_dir(), _user(), user_root() (+2 more)

### Community 47 - "Dark Render Screenshot"
Cohesion: 0.27
Nodes (10): Verified Dashboard Render (Dark 'Night' Theme), Filter Sidebar (run-search button, min score, source, status chips, location radio, posted-in-days, free text, new-only toggle), Preliminary (heuristic) Score Label - automatic rating without LLM, Job Detail Panel (big score badge, matched/missing skill chips, tip, notes, save/open buttons), Jobs Table with Score Bars (score, role, company, location, source, days, rating, status, link), KPI Cards (matching jobs, new today, strong match 75+, applied), Dark 'Night' Theme (purple accent on near-black), RTL Hebrew Layout (sidebar on right) (+2 more)

### Community 48 - "Light Render Screenshot"
Cohesion: 0.27
Nodes (10): Verified Dashboard Render (Light 'Sea' Theme), Preliminary (Heuristic) Score Label, Job Detail Panel (score badge, matched/missing skill chips, tip, notes), Jobs Table with Score Bars, KPI Cards (matching jobs, new today, strong match 75+, applied), RTL Hebrew Dashboard Layout, Find New Jobs (Run Now) Button + Last Run Summary, Light 'Sea' Theme (teal accent palette) (+2 more)

### Community 49 - "Job Detail Panel"
Cohesion: 0.22
Nodes (9): claude_panel(), detail_panel(), datetime, Two short lines; every number is isolated with <bdi> so Hebrew and digits keep t, The "CV sent" button, or when it was sent and an undo., The writing for one job goes to Claude on the person's subscription, not the API, run_summary_html(), sent_controls() (+1 more)

### Community 50 - "Dark Dashboard Screenshot"
Cohesion: 0.28
Nodes (9): Dashboard Dark Mode Screenshot, Hebrew RTL Layout, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, score, sent, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Night Dark Theme (teal accent), Sidebar Filters (search text, min score slider, source select, location), Sidebar Run Controls (find next job button, smart agent toggle, last run stats) (+1 more)

### Community 51 - "Cross-source Dedupe"
Cohesion: 0.28
Nodes (8): dedupe_batch(), is_new(), Job, Dedupe: the same posting (same id) or the same role on several boards (same comp, Lower is better: company boards (full descriptions) beat JobSpy beat remote boar, Drop repeated ids; for the same company|title keep the best source (board > jobs, Not stored yet, neither as this posting nor as the same role from another board., source_priority()

### Community 52 - "Figma Night Split Screen"
Cohesion: 0.25
Nodes (9): Figma 8:27 Dark Moody Split Screen (Jobs tab mockup), Dark "Night" Theme (near-black bg, violet accent), Hebrew RTL Tab Bar (jobs, pipeline, insights, sources, profile), Preliminary (heuristic) score label - automatic, no LLM, Job Detail Panel (big score badge, matched/missing skill chips, tip, notes, save/open buttons), Jobs Table with Score Bars (score, role, company, location, source, days, assessment, status, link), KPI Cards Row (matching jobs, new today, strong match 75+, applications submitted), Skill Chips (blue = matched, red = missing) (+1 more)

### Community 53 - "SerpAPI Parser"
Cohesion: 0.39
Nodes (7): clean(), Coerce None / NaN / non-strings to a stripped string., parse_serpapi(), posted_at_to_iso(), Google Jobs through SerpAPI (optional; skipped without SERPAPI_API_KEY).  Goog, Google's relative `posted_at` ("2 days ago", "30+ days ago", "Just posted") -> ', datetime

### Community 54 - "Sidebar Preferences"
Cohesion: 0.29
Nodes (8): experience_toggle(), owner_label(), Write non-default settings to the URL; defaults are left out to keep it short., The "experience limit" view toggle, worded for this user's limit; none when ther, save_prefs(), sidebar(), user_picker(), question()

### Community 55 - "Run Controls"
Cohesion: 0.36
Nodes (8): _health_url(), is_running(), local_llm_down(), True when the agent's local model server (agent.llm.base_url) does not answer., Live log while a run is going; only this fragment polls, the controls stay still, run_active(), run_controls(), run_status()

### Community 56 - "Light Dashboard Screenshot"
Cohesion: 0.32
Nodes (8): Dashboard Screenshot (Light Theme), Hebrew RTL UI with Sea (light purple) theme, Job Sources Shown (comeet, techmap, jobspy:linkedin, jobspy:indeed, workday), Jobs Table (role, company, location, source, days, note, sent checkbox, status, link), KPI Cards (matching jobs, new today, strong match 75+, CVs sent), Minimum Match Score Slider, Sidebar: Run Search Button, Smart Agent Toggle, Filters, Dashboard Tabs (Jobs, Pipeline, Insights, Sources, Profile)

### Community 57 - "Figma Editorial Screen"
Cohesion: 0.32
Nodes (8): Figma 8:665 Muted Editorial Dashboard Screen, Job Detail Panel (score badge, matched/missing skills, tip, notes, actions), Jobs Table with Score Bars, KPI Row (matching jobs, new today, strong match 75+, applications submitted), Muted Editorial Visual Style, Preliminary (heuristic, no-LLM) Score Label, RTL Hebrew Tab Navigation (Jobs/Pipeline/Insights/Sources/Profile), Matched vs Missing Skills (skill gap)

### Community 58 - "Handoff and Isolation"
Cohesion: 0.33
Nodes (6): Run lock (runlock.py, run.lock), handoff.py per-job brief, job-dashboard skill, Prepare application with Claude button, Per-session user/DB selection, Test isolation via env vars (JOBHUNTER_DB/RUN_DIR/USERS_DIR)

### Community 59 - "Render Compare Tool"
Cohesion: 0.60
Nodes (5): Path, main(), Render the running dashboard and put it next to the Figma reference.  Usage (fro, render(), side_by_side()

### Community 60 - "Company Board Fetch"
Cohesion: 0.47
Nodes (6): collect_company_boards(), entry_label(), _one_company(), How a companies.yaml entry is named in errors: the slug, or the Workday tenant., Fetch every company in companies.yaml. `limit` caps jobs kept per company., Any

### Community 61 - "Plugin State Types"
Cohesion: 0.33
Nodes (5): LastRun, Phase, PluginState, Progress, Tests

### Community 62 - "User Switching"
Cohesion: 0.40
Nodes (5): on_add_user(), Start the other user's view clean: filters, table edits and run state belong to, switch_user(), parse_titles(), Job titles typed in the form, one per line or comma-separated.

### Community 64 - "SerpAPI Tests"
Cohesion: 0.50
Nodes (4): _fake_serpapi(), Record the queries sent to SerpAPI; answer each with the sample fixture., test_serpapi_falls_back_to_search_queries(), test_serpapi_uses_its_own_query_list()

## Knowledge Gaps
- **64 isolated node(s):** `BASH_RULES`, `Verdict`, `RUN`, `EMPTY`, `progress` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Job` connect `TechMap Getro SerpAPI Sources` to `Users and CV Profile`, `Job Filters`, `Agent Loop Tests`, `SQLite Storage`, `ATS Board Collectors`, `Agent Loop Tools`, `Collector Registry`, `Named Users`, `Collector Tests`, `Dashboard Tests`, `Remote Job Boards`, `Search Pipeline Nodes`, `Matcher Scoring`, `Matcher Tests`, `Posting Details Fetcher`, `JobSpy Collector`, `CV Personalization`, `DB Tests`, `Agent Tool Schemas`, `Handoff Tests`, `Shared HTTP Session`, `Getro and Job Model`, `Cross-source Dedupe`, `SerpAPI Parser`, `Company Board Fetch`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `load_config()` connect `Config Loading` to `Users and CV Profile`, `Job Filters`, `Agent Loop Graph`, `Agent Loop Tests`, `Agent Precision Report`, `Collector Registry`, `Named Users`, `Run Directory Paths`, `Search Pipeline Nodes`, `Matcher Tests`, `Dashboard User Forms`, `CV Personalization`, `DB Tests`, `Company Sync Script`, `User Switching`, `Test Conftest`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `CandidateProfile` connect `Users and CV Profile` to `Agent Tool Schemas`, `Job Filters`, `Agent Loop Tests`, `Agent Loop Tools`, `TechMap Getro SerpAPI Sources`, `Getro and Job Model`, `Collector Registry`, `Search Pipeline Nodes`, `Job Detail Panel`, `Matcher Scoring`, `Matcher Tests`, `Dashboard User Forms`, `CV Personalization`, `Config Loading`, `Dashboard Tabs`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 60 inferred relationships involving `Job` (e.g. with `AgentContext` and `NoArgs`) actually correct?**
  _`Job` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `CollectorResult` (e.g. with `Job` and `RateLimitWatch`) actually correct?**
  _`CollectorResult` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `CandidateProfile` (e.g. with `AgentContext` and `NoArgs`) actually correct?**
  _`CandidateProfile` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `AgentContext` (e.g. with `AgentUnavailable` and `LoopState`) actually correct?**
  _`AgentContext` has 11 INFERRED edges - model-reasoned connections that need verification._