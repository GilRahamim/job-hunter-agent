import copy

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from jobhunter import agent_loop, db
from jobhunter.agent_loop import graph, tools
from jobhunter.collectors.base import CollectorResult
from jobhunter.collectors.details import Posting
from jobhunter.config import load_config
from jobhunter.models import CandidateProfile, Job

CV = "Dana Levi\nJunior Software Engineer\nSkills: Python, SQL, LangChain, RAG, Docker\n"

PY = Job("jobspy:linkedin", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel",
         description="Python SQL Docker backend services. No experience required.")
AI = Job("jobspy:linkedin", "AI Engineer", "Beta", "https://b/1", location="Haifa, Israel",
         description="Python LangChain RAG agents")
SENIOR = Job("jobspy:linkedin", "Senior Backend Developer", "Gamma", "https://c/1", location="Haifa, Israel")
BOARD = Job("greenhouse", "Data Analyst", "Delta", "https://d/1", location="Tel Aviv, Israel",
            description="SQL Python dashboards")


def call(name, args=None, i=[0]):
    i[0] += 1
    return AIMessage("", tool_calls=[{"name": name, "args": args or {}, "id": f"c{i[0]}"}])


class ScriptedModel:
    """Replays a fixed list of replies; records the messages it was shown."""

    def __init__(self, script):
        self.script = list(script)
        self.seen = []

    def bind_tools(self, tools):
        return self

    def with_structured_output(self, cls):
        class S:
            def invoke(self, messages):
                return CandidateProfile(skills=["Python", "SQL", "RAG"], seniority="junior")
        return S()

    def invoke(self, messages):
        self.seen.append(list(messages))
        return self.script.pop(0) if self.script else AIMessage("DONE")


def tool_outputs(model):
    return [m.content for m in model.seen[-1] if isinstance(m, ToolMessage)]


@pytest.fixture
def env(tmp_path, monkeypatch):
    cv_dir = tmp_path / "cv"
    cv_dir.mkdir()
    (cv_dir / "cv.txt").write_text(CV, encoding="utf-8")
    cfg = copy.deepcopy(load_config())
    cfg["profile"]["cv_dir"] = str(cv_dir)
    cfg["agent"].update(goal_matches=1, min_match_score=70, max_steps=10, max_searches=3, llm={})
    calls = []

    def fake_collect(config, only=None, limit=None):
        calls.append((tuple(only), list(config["search"]["queries"])))
        found = [BOARD] if "ats" in only else [PY, AI, SENIOR]           # company_pages = ats + techmap
        name = only[0]
        return ([CollectorResult(name, found)],
                [{"source": name, "fetched": len(found), "error": None, "duration_s": 0.1}])

    monkeypatch.setattr(tools, "collect_all", fake_collect)
    return cfg, str(tmp_path / "jobs.db"), calls


def use(monkeypatch, model):
    monkeypatch.setattr(graph, "get_llm", lambda cfg: model)


def test_goal_reached_saves_agent_scores(env, monkeypatch):
    cfg, path, calls = env
    model = ScriptedModel([
        call("get_profile"),
        call("search_jobs", {"query": "Junior Python Developer", "source": "linkedin"}),
        call("read_posting", {"job_id": PY.id}),
        call("save_match", {"job_id": PY.id, "score": 85, "reason": "Python and SQL fit"}),
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path)
    stats = result["stats"]
    assert stats["stop_reason"] == "goal_reached" and stats["steps"] == 4
    assert calls == [(("jobspy",), ["Junior Python Developer"])]          # the model's query was used
    assert stats["filtered_by_reason"] == {"senior": 1}
    saved = {j["id"]: j for j in db.all_jobs(path=path)}
    assert set(saved) == {PY.id, AI.id}                                   # senior job never stored
    assert saved[PY.id]["score"] == 85 and saved[PY.id]["scored_by"].startswith("agent:")
    assert saved[PY.id]["verdict"] == "strong" and saved[PY.id]["reasons"] == "Python and SQL fit"
    assert saved[AI.id]["scored_by"] == "heuristic"
    run = db.last_runs(1, path)[0]
    assert run["finished"] and run["stats"]["mode"].startswith("agent:")


def test_filtered_unknown_and_unread_jobs_are_rejected(env, monkeypatch):
    cfg, path, _ = env
    model = ScriptedModel([
        call("search_jobs", {"query": "developer", "source": "linkedin"}),
        call("read_posting", {"job_id": SENIOR.id}),                       # filtered out -> unknown
        call("save_match", {"job_id": AI.id, "score": 90, "reason": "x"}),  # not read yet
        call("save_match", {"job_id": AI.id, "score": 150, "reason": "x"}),  # invalid score
        call("search_jobs", {"query": "x", "source": "facebook"}),
        call("no_such_tool"),
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path)
    outs = tool_outputs(model)
    assert "unknown job_id" in outs[1]
    assert "read_posting" in outs[2]
    assert "invalid arguments" in outs[3]
    assert "unknown source" in outs[4]
    assert "unknown tool" in outs[5]
    assert result["matches"] == {} and result["stats"]["stop_reason"] == "model_stopped"


def test_title_sources_fetch_once_and_match_query(env, monkeypatch):
    cfg, path, calls = env
    model = ScriptedModel([
        call("search_jobs", {"query": "data", "source": "company_pages"}),
        call("search_jobs", {"query": "python", "source": "company_pages"}),
    ])
    use(monkeypatch, model)
    agent_loop.run(cfg, db_path=path, dry_run=True)
    assert [c[0] for c in calls] == [("ats", "techmap", "getro")]         # cached after the first search
    outs = tool_outputs(model)
    assert BOARD.id in outs[0] and "0 postings matched" in outs[1]


def test_search_budget_and_step_limit(env, monkeypatch):
    cfg, path, calls = env
    cfg["agent"].update(max_searches=1, max_steps=3)
    model = ScriptedModel([call("search_jobs", {"query": f"q{i}", "source": "linkedin"}) for i in range(5)])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path)
    assert len(calls) == 1 and "budget used up" in tool_outputs(model)[-1]
    assert result["stats"]["stop_reason"] == "step_limit" and result["stats"]["steps"] == 3


def test_known_jobs_hidden_and_status_kept(env, monkeypatch):
    cfg, path, _ = env
    row = PY.to_dict() | {"score": 50.0, "scored_by": "heuristic"}
    db.upsert_jobs([row], path)
    db.update_status(PY.id, "applied", "sent", path)
    model = ScriptedModel([call("search_jobs", {"query": "python", "source": "linkedin"})])
    use(monkeypatch, model)
    agent_loop.run(cfg, db_path=path)
    assert PY.id not in tool_outputs(model)[0]
    job = next(j for j in db.all_jobs(path=path) if j["id"] == PY.id)
    assert job["status"] == "applied" and job["notes"] == "sent" and job["score"] == 50.0


def test_nudge_once_then_stop(env, monkeypatch):
    cfg, path, _ = env
    model = ScriptedModel([AIMessage("I think I'm finished"), AIMessage("still nothing")])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path, dry_run=True)
    assert result["stats"]["stop_reason"] == "model_stopped" and result["stats"]["steps"] == 2
    assert db.last_runs(5, path) == []                                    # dry run writes nothing


def test_model_error_keeps_results(env, monkeypatch):
    cfg, path, _ = env

    class Failing(ScriptedModel):
        def invoke(self, messages):
            if self.script:
                return super().invoke(messages)
            raise RuntimeError("credit balance too low")

    model = Failing([call("search_jobs", {"query": "python", "source": "linkedin"})])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path)
    assert result["stats"]["stop_reason"].startswith("model error")
    assert len(db.all_jobs(path=path)) == 2                               # candidates still saved


def test_no_llm_raises_agent_unavailable(env, monkeypatch):
    cfg, path, _ = env
    use(monkeypatch, None)
    with pytest.raises(agent_loop.AgentUnavailable):
        agent_loop.run(cfg, db_path=path)


def test_old_postings_are_compacted_for_the_model(env, monkeypatch):
    cfg, path, _ = env
    model = ScriptedModel([
        call("search_jobs", {"query": "developer", "source": "linkedin"}),
        call("read_posting", {"job_id": PY.id}),
        call("read_posting", {"job_id": AI.id}),
    ])
    use(monkeypatch, model)
    agent_loop.run(cfg, db_path=path, dry_run=True)
    reads = [m.content for m in model.seen[-1] if isinstance(m, ToolMessage) and m.name == "read_posting"]
    assert graph.POSTING_CUT_NOTE in reads[0] and "Junior Python Developer" in reads[0]
    assert "backend services" not in reads[0] and "LangChain RAG agents" in reads[1]


def test_local_openai_compatible_server_needs_no_key(monkeypatch):
    from jobhunter import llm as llm_mod
    seen = {}
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("langchain.chat_models.init_chat_model",
                        lambda model, **kw: seen.update(model=model, **kw) or "chat")
    cfg = {"llm": {"provider": "openai", "model": "qwen", "temperature": 0, "max_workers": 2,
                   "base_url": "http://localhost:1234/v1", "max_tokens": 2048}}
    assert llm_mod.get_llm(cfg) == "chat"
    assert seen["base_url"] == "http://localhost:1234/v1" and seen["api_key"] == llm_mod.LOCAL_API_KEY
    assert seen["max_tokens"] == 2048 and "max_workers" not in seen
    cfg["llm"].pop("base_url")
    assert llm_mod.get_llm(cfg) is None                                   # real OpenAI still needs a key


def test_agent_llm_override():
    cfg = {"llm": {"provider": "anthropic", "model": "m", "temperature": 0},
           "agent": {"llm": {"provider": "ollama", "model": "qwen3:8b"}}}
    merged = graph.agent_llm_config(cfg)["llm"]
    assert merged == {"provider": "ollama", "model": "qwen3:8b", "temperature": 0}


GROUPS = {"AI / ML": ["AI Engineer", "LLM Engineer"], "Data": ["Data Analyst", "Data Scientist"],
          "Software": ["Software Engineer", "Python Developer"]}


@pytest.mark.parametrize("query,expected", [
    ("Junior Data Analyst", ["Data"]),
    ("data", ["Data"]),
    ("AI", ["AI / ML"]),
    ("Junior Python Developer", ["Software"]),
    ("Engineer", ["AI / ML", "Software"]),
    ("Product Manager", []),
])
def test_query_groups(query, expected):
    assert tools.query_groups(query, GROUPS) == expected


def test_search_reports_uncovered_groups_and_caps_a_group(env, monkeypatch):
    cfg, path, _ = env
    cfg["agent"].update(role_groups=GROUPS, max_searches=5, max_searches_per_group=1)
    model = ScriptedModel([
        call("search_jobs", {"query": "AI Engineer", "source": "linkedin"}),
        call("search_jobs", {"query": "LLM Engineer", "source": "linkedin"}),
    ])
    use(monkeypatch, model)
    agent_loop.run(config=cfg, db_path=path, dry_run=True)
    first, second = tool_outputs(model)[:2]
    assert "Role groups not searched yet: Data, Software" in first
    assert second.startswith("ERROR: role group AI / ML already has 1 searches")
    system = model.seen[0][0].content
    assert "- Data: Data Analyst, Data Scientist" in system and "at most 1 per role group" in system


def test_linkedin_queries_are_forced_junior(env, monkeypatch):
    cfg, path, calls = env
    model = ScriptedModel([call("search_jobs", {"query": "AI Engineer", "source": "linkedin"}),
                           call("search_jobs", {"query": "Graduate Data Analyst", "source": "linkedin"})])
    use(monkeypatch, model)
    agent_loop.run(cfg, db_path=path, dry_run=True)
    assert [q for _, q in calls] == [["Junior AI Engineer"], ["Graduate Data Analyst"]]
    assert "Searched as 'Junior AI Engineer'" in tool_outputs(model)[0]


def test_save_refuses_jobs_that_need_experience(env, monkeypatch):
    cfg, path, _ = env
    # passed the filters under a looser config, then the agent tries to save it
    loose = copy.deepcopy(cfg)
    loose["filters"]["max_required_years"] = None
    exp = Job("jobspy:linkedin", "Python Developer", "Eps", "https://e/1", location="Tel Aviv, Israel",
              description="Python. 3+ years of experience required.")
    monkeypatch.setattr(tools, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("jobspy", [exp])], [{"source": "jobspy", "fetched": 1, "error": None,
                                              "duration_s": 0.1}]))
    ctx = tools.AgentContext(config=loose, profile=CandidateProfile(skills=["Python"]),
                             known_ids=set(), known_keys=set())
    tools.search_jobs(ctx, "Python Developer", "linkedin")
    assert exp.id in ctx.candidates
    tools.read_posting(ctx, exp.id)
    ctx.config = cfg                                     # the real, junior-only config
    out = tools.save_match(ctx, exp.id, 90, "fits")
    assert out.startswith("REFUSED") and "experience" in out and not ctx.matches


def test_refused_and_closed_jobs_are_not_stored(env, monkeypatch):
    cfg, path, _ = env
    loose = copy.deepcopy(cfg)
    loose["filters"]["max_required_years"] = None
    exp = Job("jobspy:linkedin", "Python Developer", "Eps", "https://e/1", location="Tel Aviv, Israel",
              description="Python. 4+ years of experience required.")
    gone = Job("jobspy:linkedin", "Junior Python Developer", "Zed", "https://il.linkedin.com/jobs/view/py-at-zed-1234567",
               location="Tel Aviv, Israel")
    fine = Job("jobspy:linkedin", "Junior Python Developer", "Ok", "https://o/1", location="Tel Aviv, Israel",
               description="Python, no experience needed")
    monkeypatch.setattr(tools, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("jobspy", [exp, gone, fine])], [{"source": "jobspy", "fetched": 3, "error": None,
                                                          "duration_s": 0.1}]))
    monkeypatch.setattr(tools, "fetch_posting", lambda job: Posting("Junior role", closed=True))
    ctx = tools.AgentContext(config=loose, profile=CandidateProfile(skills=["Python"]),
                             known_ids=set(), known_keys=set())
    tools.search_jobs(ctx, "Python Developer", "linkedin")
    tools.read_posting(ctx, gone.id)
    ctx.config = cfg                                     # the real, junior-only config
    rows = graph.result_rows(ctx, "hash", "m")
    assert [r["id"] for r in rows] == [fine.id]          # 4+ years and closed jobs are not stored


def test_agent_fetches_linkedin_descriptions(env, monkeypatch):
    cfg, path, _ = env
    seen = []
    monkeypatch.setattr(tools, "collect_all", lambda config, only=None, limit=None: (
        seen.append(config["sources"]["jobspy"]["fetch_linkedin_descriptions"]) or [], []))
    ctx = tools.AgentContext(config=cfg, profile=CandidateProfile(), known_ids=set(), known_keys=set())
    tools.search_jobs(ctx, "Junior Python Developer", "linkedin")
    assert seen == [True]


def test_stop_request_ends_the_run_and_keeps_results(env, monkeypatch, tmp_path):
    from jobhunter import stop
    cfg, path, _ = env

    class StopAfterSearch(ScriptedModel):
        def invoke(self, messages):
            reply = super().invoke(messages)
            if reply.tool_calls and reply.tool_calls[0]["name"] == "search_jobs":
                stop.request_stop()                      # the user flips the toggle mid-run
            return reply

    model = StopAfterSearch([call("search_jobs", {"query": "Junior Python Developer", "source": "linkedin"}),
                             call("read_posting", {"job_id": PY.id})])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path)
    assert result["stats"]["stop_reason"] == "stopped_by_user" and result["stats"]["steps"] == 1
    assert {j["id"] for j in db.all_jobs(path=path)} == {PY.id, AI.id}    # found jobs are still saved


def test_stale_stop_request_is_cleared_but_fresh_one_kept(tmp_path, monkeypatch):
    import os
    import time

    from jobhunter import stop
    stop.request_stop()
    stop.clear_stale_stop()
    assert stop.stop_requested()                         # fresh: switched on while the run was starting
    old = time.time() - 3600
    os.utime(stop.stop_path(), (old, old))
    stop.clear_stale_stop()
    assert not stop.stop_requested()


@pytest.mark.parametrize("title,query,hit", [
    ("AI Engineer", "ai", True),
    ("Retail Data Analyst", "ai", False),              # "ai" inside "retail"
    ("Maintenance Technician", "ai", False),
    ("Software Engineering Intern", "software engineer", True),
    ("Junior Data Analyst", "data analyst", True),
])
def test_board_queries_match_title_words_not_substrings(title, query, hit):
    assert tools.title_matches(title, query.split()) is hit


def test_board_query_ignores_junior_words_in_the_title_match(env):
    cfg, _, _ = env
    ctx = tools.AgentContext(config=cfg, profile=CandidateProfile(), known_ids=set(), known_keys=set())
    ai = Job("greenhouse", "AI Engineer", "A", "https://a/ai")
    student = Job("greenhouse", "Software Student", "B", "https://b/st")
    ctx.cache["company_pages"] = [ai, student]
    assert tools._fetch(ctx, "company_pages", "Junior AI Engineer") == [ai]     # junior check is the filter's job
    assert tools._fetch(ctx, "company_pages", "Student") == [student]          # only junior words: keep them


def test_agent_cannot_save_a_closed_linkedin_job(env, monkeypatch):
    cfg, path, _ = env
    job = Job("jobspy:linkedin", "Junior Python Developer", "Zed",
              "https://il.linkedin.com/jobs/view/py-at-zed-1234567", location="Tel Aviv, Israel",
              description="Junior Python role")
    monkeypatch.setattr(tools, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("jobspy", [job])], [{"source": "jobspy", "fetched": 1, "error": None,
                                              "duration_s": 0.1}]))
    monkeypatch.setattr(tools, "fetch_posting", lambda j: Posting("", closed=True))
    ctx = tools.AgentContext(config=cfg, profile=CandidateProfile(skills=["Python"]),
                             known_ids=set(), known_keys=set())
    tools.search_jobs(ctx, "Junior Python Developer", "linkedin")
    assert tools.read_posting(ctx, job.id).startswith("CLOSED")
    assert tools.save_match(ctx, job.id, 90, "fits").startswith("REFUSED") and not ctx.matches
    assert job.description == "Junior Python role"           # the search's description is kept


def calls(*pairs):
    """One model turn with several tool calls: calls(("read_posting", {...}), ("read_posting", {...}))."""
    msgs = [call(name, args) for name, args in pairs]
    return AIMessage("", tool_calls=[m.tool_calls[0] for m in msgs])


def test_same_role_on_two_sources_is_kept_once(env, monkeypatch):
    cfg, path, _ = env
    dup = Job("jobspy:linkedin", "Data Analyst", "Delta", "https://li/9", location="Tel Aviv, Israel",
              description="SQL dashboards")
    monkeypatch.setattr(tools, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult(only[0], [BOARD] if "ats" in only else [dup])],
        [{"source": only[0], "fetched": 1, "error": None, "duration_s": 0.1}]))
    model = ScriptedModel([
        call("search_jobs", {"query": "Junior Data Analyst", "source": "linkedin"}),
        call("search_jobs", {"query": "data analyst", "source": "company_pages"}),
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path, dry_run=True)
    assert "1 postings matched, 0 new" in tool_outputs(model)[1]          # same company|title as dup
    assert [r["id"] for r in result["rows"]] == [dup.id]


def test_batched_reads_are_shown_in_full_and_saved_next_turn(env, monkeypatch):
    cfg, path, _ = env
    cfg["agent"].update(goal_matches=2)
    model = ScriptedModel([
        call("search_jobs", {"query": "developer", "source": "linkedin"}),
        calls(("read_posting", {"job_id": PY.id}), ("read_posting", {"job_id": AI.id})),
        calls(("save_match", {"job_id": PY.id, "score": 80, "reason": "a"}),
              ("save_match", {"job_id": AI.id, "score": 75, "reason": "b"})),
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path, dry_run=True)
    view = " ".join(str(m.content) for m in model.seen[2])                # the turn that saves
    assert "backend services" in view and "LangChain RAG agents" in view  # both postings in full
    assert graph.POSTING_CUT_NOTE not in view
    assert result["stats"]["stop_reason"] == "goal_reached" and result["stats"]["steps"] == 3


def test_save_in_the_same_turn_as_the_read_is_refused(env, monkeypatch):
    cfg, path, _ = env
    model = ScriptedModel([
        call("search_jobs", {"query": "developer", "source": "linkedin"}),
        calls(("read_posting", {"job_id": PY.id}),
              ("save_match", {"job_id": PY.id, "score": 80, "reason": "blind"})),
        call("save_match", {"job_id": PY.id, "score": 80, "reason": "seen"}),
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path, dry_run=True)
    assert "same turn" in tool_outputs(model)[2]
    assert result["matches"][PY.id]["reason"] == "seen" and result["stats"]["stop_reason"] == "goal_reached"


def test_searches_on_a_loaded_board_list_are_free(env, monkeypatch):
    cfg, path, calls_ = env
    cfg["agent"].update(max_searches=2)
    model = ScriptedModel([
        call("search_jobs", {"query": "data", "source": "company_pages"}),     # loads the list: charged
        call("search_jobs", {"query": "python", "source": "company_pages"}),   # free
        call("search_jobs", {"query": "Junior Python Developer", "source": "linkedin"}),
        call("search_jobs", {"query": "Junior AI Engineer", "source": "linkedin"}),
        call("search_jobs", {"query": "analyst", "source": "company_pages"}),  # still free
    ])
    use(monkeypatch, model)
    result = agent_loop.run(cfg, db_path=path, dry_run=True)
    outs = tool_outputs(model)
    assert "Searches left: 1" in outs[0] and "was free" in outs[1] and "Searches left: 1" in outs[1]
    assert "Searches left: 0" in outs[2]
    assert "budget used up" in outs[3] and "company_pages are still free" in outs[3]
    assert "was free" in outs[4] and len(calls_) == 2
    assert result["stats"]["searches"] == 4 and result["stats"]["charged_searches"] == 2


def test_next_run_is_told_which_queries_worked(env, monkeypatch):
    cfg, path, _ = env
    cfg["agent"].update(memory_runs=5)
    db.finish_run(db.start_run(path), {"mode": "llm:m", "kept": 3}, [], path)  # a pipeline run: ignored
    first = ScriptedModel([
        call("search_jobs", {"query": "Junior Python Developer", "source": "linkedin"}),
        call("read_posting", {"job_id": PY.id}),
        call("save_match", {"job_id": PY.id, "score": 85, "reason": "fits"}),
    ])
    use(monkeypatch, first)
    result = agent_loop.run(cfg, db_path=path)
    assert result["stats"]["queries"] == [{"query": "Junior Python Developer", "source": "linkedin",
                                           "found": 3, "new": 2, "read": 1, "saved": 1, "strong": 1}]
    assert "What your searches found" not in first.seen[0][1].content    # no history yet

    second = ScriptedModel([call("search_jobs", {"query": "Junior AI Engineer", "source": "remote_boards"})])
    use(monkeypatch, second)
    agent_loop.run(cfg, db_path=path)
    start = second.seen[0][1].content
    assert "last 1 agent run(s)" in start
    assert '"Junior Python Developer" on linkedin: searched 1x, 2 new jobs, 1 saved (1 strong)' in start

    third = ScriptedModel([])
    use(monkeypatch, third)
    agent_loop.run(cfg, db_path=path, dry_run=True)
    start = third.seen[0][1].content
    assert "last 2 agent run(s)" in start
    assert start.index("Junior Python Developer") < start.index("Queries that led to no saved job")
    assert '"Junior AI Engineer" on remote_boards: searched 1x' in start.split("no saved job:")[1]

    cfg["agent"].update(memory_runs=0)
    off = ScriptedModel([])
    use(monkeypatch, off)
    agent_loop.run(cfg, db_path=path, dry_run=True)
    assert "What your searches found" not in off.seen[0][1].content
