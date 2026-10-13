import copy
import os

import pytest

from jobhunter import agent, db
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
    with agent.run_lock(lock):
        assert lock.read_text() == str(os.getpid())
        assert agent.pid_alive(os.getpid())
    assert not lock.exists()
    lock.write_text("999999999")                                  # stale pid
    with agent.run_lock(lock):
        pass


def test_lock_rejects_live_foreign_pid(tmp_path, monkeypatch):
    lock = tmp_path / "run.lock"
    lock.write_text("4242")
    monkeypatch.setattr(agent, "pid_alive", lambda pid: True)
    with pytest.raises(agent.RunLocked):
        agent.run_lock(lock).__enter__()
