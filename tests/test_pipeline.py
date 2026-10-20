import copy
import os

import pytest

from jobhunter import agent, db, runlock
from jobhunter.collectors.base import CollectorResult
from jobhunter.config import load_config
from jobhunter.models import CandidateProfile, Job, JobMatch

CV = "Dana Levi\nJunior Software Engineer\nSkills: Python, SQL, LangChain, RAG, Docker\n"


def jobs():
    return [
        Job("greenhouse", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel",
            description="Python SQL Docker backend services"),
        Job("jobspy:linkedin", "Junior Python Developer", "Acme Ltd", "https://linkedin/1",
            location="Tel Aviv, Israel", description="short"),          # same role, other board
        Job("remotive", "AI Engineer", "Beta", "https://b/1", is_remote=True, remote_region="Worldwide",
            description="Python LangChain RAG"),
        Job("greenhouse", "Senior Backend Developer", "Gamma", "https://c/1", location="Haifa, Israel"),
        Job("greenhouse", "Python Developer", "Delta", "https://d/1", location="Austin, Texas, United States"),
        Job("greenhouse", "Office Manager", "Eps", "https://e/1", location="Tel Aviv, Israel"),
    ]


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def with_structured_output(self, cls):
        outer = self

        class S:
            def invoke(self, messages):
                if cls is CandidateProfile:                      # profile extraction
                    return CandidateProfile(skills=["Python", "SQL", "RAG"], seniority="junior")
                outer.calls += 1
                return JobMatch(score=88, verdict="strong", reasons="fits", matching_skills=["Python"])
        return S()


@pytest.fixture
def env(tmp_path, monkeypatch):
    cv_dir = tmp_path / "cv"
    cv_dir.mkdir()
    (cv_dir / "cv.txt").write_text(CV, encoding="utf-8")
    cfg = copy.deepcopy(load_config())
    cfg["profile"]["cv_dir"] = str(cv_dir)

    def fake_collect(config, only=None, limit=None):
        found = jobs()
        return ([CollectorResult("ats", found), CollectorResult("jobspy", error="blocked")],
                [{"source": "ats", "fetched": len(found), "error": None, "duration_s": 0.1},
                 {"source": "jobspy", "fetched": 0, "error": "blocked", "duration_s": 0.2}])

    monkeypatch.setattr(agent, "collect_all", fake_collect)
    monkeypatch.setattr(agent, "get_llm", lambda cfg: None)
    return cfg, str(tmp_path / "jobs.db")


def test_heuristic_run_saves_filters_and_records_health(env):
    cfg, path = env
    state = agent.run(cfg, db_path=path, no_llm=True)
    stats = state["stats"]
    assert stats["collected"] == 6 and stats["new"] == 5          # cross-board duplicate merged
    assert stats["filtered_by_reason"] == {"location": 1, "role": 1, "senior": 1}
    saved = db.all_jobs(path=path)
    assert {j["title"] for j in saved} == {"Junior Python Developer", "AI Engineer"}
    linkedin_dup = [j for j in saved if j["source"].startswith("jobspy")]
    assert not linkedin_dup                                       # company-board version won
    assert all(j["scored_by"] == "heuristic" for j in saved)
    run = db.last_runs(1, path)[0]
    assert run["finished"] and run["stats"]["mode"] == "heuristic"
    health = {h["source"]: h for h in db.health_for_run(run["id"], path)}
    assert health["jobspy"]["error"] == "blocked" and health["ats"]["fetched"] == 6


def test_second_run_adds_nothing(env):
    cfg, path = env
    agent.run(cfg, db_path=path, no_llm=True)
    again = agent.run(cfg, db_path=path, no_llm=True)["stats"]
    # dropped jobs are not stored, so they are re-seen and re-dropped; nothing new is kept or scored
    assert again["kept"] == 0 and again["known"] == 2 and again["prescored"] == 0
    assert len(db.all_jobs(path=path)) == 2 and len(db.last_runs(5, path)) == 2


def test_user_status_survives_rerun_and_rescore(env, monkeypatch):
    cfg, path = env
    agent.run(cfg, db_path=path, no_llm=True)
    target = db.all_jobs(path=path)[0]["id"]
    db.update_status(target, "applied", "sent", path)
    monkeypatch.setattr(agent, "get_llm", lambda c: FakeLLM())
    agent.run(cfg, db_path=path)                                  # LLM now available -> heuristic jobs re-scored
    job = next(j for j in db.all_jobs(path=path) if j["id"] == target)
    assert job["status"] == "applied" and job["notes"] == "sent"
    assert job["scored_by"].startswith("llm:") and job["score"] == 88


def test_llm_run_scores_top_jobs(env, monkeypatch):
    cfg, path = env
    llm = FakeLLM()
    monkeypatch.setattr(agent, "get_llm", lambda c: llm)
    state = agent.run(cfg, db_path=path)
    assert state["stats"]["llm_scored"] == llm.calls > 0
    assert all(j["scored_by"].startswith("llm:") for j in db.all_jobs(path=path) if j["score"] == 88)
    again = agent.run(cfg, db_path=path)["stats"]
    assert again["kept"] == 0 and llm.calls == state["stats"]["llm_scored"]    # nothing re-scored


def test_llm_scoring_sees_the_users_choices(env, monkeypatch):
    cfg, path = env
    agent.run(cfg, db_path=path, no_llm=True)
    liked = db.all_jobs(path=path)[0]
    db.update_status(liked["id"], "interested", path=path)
    prompts = []

    class Recording(FakeLLM):
        def with_structured_output(self, cls):
            inner = super().with_structured_output(cls)

            class S:
                def invoke(self, messages):
                    prompts.append(messages[1][1])
                    return inner.invoke(messages)
            return S()

    monkeypatch.setattr(agent, "get_llm", lambda c: Recording())
    agent.run(cfg, db_path=path)
    scoring = [p for p in prompts if p.startswith("<candidate>")]           # not the CV extraction
    assert scoring and all(f"chose to pursue: {liked['title']}" in p for p in scoring)


def test_dry_run_writes_nothing(env):
    cfg, path = env
    state = agent.run(cfg, db_path=path, no_llm=True, dry_run=True)
    assert state["rows"] and state["stats"]["dry_run"]
    assert db.all_jobs(path=path) == [] and db.last_runs(5, path) == []


def test_crash_closes_the_run_row(env, monkeypatch):
    cfg, path = env
    monkeypatch.setattr(agent, "dedupe_batch", lambda j: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        agent.run(cfg, db_path=path, no_llm=True)
    run = db.last_runs(1, path)[0]
    assert run["finished"] and "boom" in run["stats"]["error"]


def test_lock_blocks_second_run_and_ignores_stale(tmp_path):
    lock = tmp_path / "run.lock"
    with runlock.run_lock(lock):
        assert lock.read_text() == str(os.getpid())
        assert runlock.pid_alive(os.getpid())
    assert not lock.exists()
    lock.write_text("999999999")                                  # stale pid
    with runlock.run_lock(lock):
        pass


def test_lock_rejects_live_foreign_pid(tmp_path, monkeypatch):
    lock = tmp_path / "run.lock"
    lock.write_text("4242")
    monkeypatch.setattr(runlock, "pid_alive", lambda pid: True)
    with pytest.raises(runlock.RunLocked):
        runlock.run_lock(lock).__enter__()


def test_rescore_slots_are_not_wasted_on_non_junior_jobs(env, monkeypatch):
    cfg, path = env
    cfg["matching"]["llm_top_n"] = 2
    # stored before the junior filters: high pre-scores, but they need experience
    old = [Job("greenhouse", f"Python Developer {i}", f"Old{i}", f"https://old/{i}", location="Tel Aviv, Israel",
               description="Python. 5+ years of experience.") for i in range(3)]
    ok = Job("greenhouse", "Junior Python Developer", "Fine", "https://fine/1", location="Tel Aviv, Israel",
             description="Python and SQL, no experience needed.")
    db.upsert_jobs([{**j.to_dict(), "prescore": 90 - i, "score": 90 - i, "scored_by": "heuristic", "cv_hash": "x"}
                    for i, j in enumerate(old)] + [{**ok.to_dict(), "prescore": 50, "score": 50,
                                                    "scored_by": "heuristic", "cv_hash": "x"}], path)
    monkeypatch.setattr(agent, "collect_all", lambda config, only=None, limit=None: ([], []))
    monkeypatch.setattr(agent, "get_llm", lambda c: FakeLLM())
    state = agent.run(cfg, db_path=path)
    assert state["rescored_ids"] == {ok.id}            # the junior job is reached despite its lower pre-score


def test_heuristic_rescore_clears_a_stale_llm_verdict(env, monkeypatch):
    cfg, path = env
    monkeypatch.setattr(agent, "get_llm", lambda c: FakeLLM())
    agent.run(cfg, db_path=path)
    assert any(j["verdict"] for j in db.all_jobs(path=path))
    monkeypatch.setattr(agent, "get_llm", lambda c: None)
    agent.run(cfg, db_path=path, rescore=True)          # new CV, no LLM: heuristic scores only
    for j in db.all_jobs(path=path):
        assert j["scored_by"] == "heuristic" and j["verdict"] is None and j["reasons"] is None


def test_jobs_without_description_are_read_then_checked_for_experience(env, monkeypatch):
    cfg, path = env
    cfg["matching"]["fetch_descriptions"] = 5
    bare = Job("techmap", "Junior Python Developer", "Zed", "https://il.linkedin.com/jobs/view/py-at-zed-1234567",
               location="Tel Aviv, Israel")
    monkeypatch.setattr(agent, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("techmap", [bare])], [{"source": "techmap", "fetched": 1, "error": None, "duration_s": 0}]))
    from jobhunter.collectors import details
    monkeypatch.setattr(details, "fetch_posting",
                        lambda job: details.Posting("Python. 2+ years of experience required."))
    state = agent.run(cfg, db_path=path, no_llm=True)
    assert state["stats"]["filtered_by_reason"] == {"experience": 1} and state["stats"]["kept"] == 0


def test_new_jobs_the_llm_reads_as_experienced_are_not_saved(env, monkeypatch):
    cfg, path = env
    ok = Job("greenhouse", "Python Developer", "Ok", "https://ok/1", location="Tel Aviv, Israel",
             description="Python SQL Docker backend services")
    exp = Job("greenhouse", "Python Developer", "Exp", "https://exp/1", location="Tel Aviv, Israel",
              description="Python SQL Docker. Several years in production systems.")   # the rules read 0
    monkeypatch.setattr(agent, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("ats", [ok, exp])], [{"source": "ats", "fetched": 2, "error": None, "duration_s": 0}]))

    class YearsLLM(FakeLLM):
        def with_structured_output(self, cls):
            class S:
                def invoke(self, messages):
                    if cls is CandidateProfile:
                        return CandidateProfile(skills=["Python"], seniority="junior")
                    years = 4 if "Company: Exp\n" in messages[1][1] else 0
                    return JobMatch(score=80, verdict="strong", required_years=years)
            return S()

    monkeypatch.setattr(agent, "get_llm", lambda cfg: YearsLLM())
    cfg["matching"]["min_prescore_for_llm"] = 0
    state = agent.run(cfg, db_path=path)
    assert [r["company"] for r in db.all_jobs(path=path)] == ["Ok"]
    assert state["stats"]["filtered_by_reason"].get("experience_llm") == 1


def test_not_junior_ids_include_the_stored_years(env):
    cfg, path = env
    db.upsert_jobs([{**Job("greenhouse", "Python Developer", "A", "https://a/9").to_dict(), "required_years": 3},
                    {**Job("greenhouse", "Python Developer", "B", "https://b/9").to_dict(), "required_years": 0}],
                   path)
    ids = {r["company"]: r["id"] for r in db.all_jobs(path=path)}
    assert db.not_junior_ids(cfg, path) == {ids["A"]}


def test_closed_linkedin_jobs_are_not_saved(env, monkeypatch):
    cfg, path = env
    cfg["matching"]["fetch_descriptions"] = 5
    bare = Job("techmap", "Junior Python Developer", "Zed", "https://il.linkedin.com/jobs/view/py-at-zed-1234567",
               location="Tel Aviv, Israel")
    monkeypatch.setattr(agent, "collect_all", lambda config, only=None, limit=None: (
        [CollectorResult("techmap", [bare])], [{"source": "techmap", "fetched": 1, "error": None, "duration_s": 0}]))
    from jobhunter.collectors import details
    monkeypatch.setattr(details, "fetch_posting", lambda job: details.Posting("Junior Python role", closed=True))
    state = agent.run(cfg, db_path=path, no_llm=True)
    assert state["stats"]["filtered_by_reason"] == {"closed": 1} and not db.all_jobs(path=path)


def test_run_summary_shows_source_notes():
    import run_agent
    assert run_agent.source_status({"error": None, "warning": None}) == "ok"
    assert run_agent.source_status({"error": "boom", "warning": "x"}) == "ERROR: boom"
    assert "SERPAPI_API_KEY" in run_agent.source_status(
        {"error": None, "warning": "SERPAPI_API_KEY is not set in .env; skipped"})
