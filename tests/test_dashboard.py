from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest

from jobhunter import db
from jobhunter.models import Job

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard.py"


def _app(tmp_path, monkeypatch, jobs=()):
    st.cache_data.clear()                       # load_jobs() is cached across tests
    path = tmp_path / "jobs.db"
    monkeypatch.setenv("JOBHUNTER_DB", str(path))
    rows = []
    for i, j in enumerate(jobs):
        row = j.to_dict()
        row.update(score=80 - i, prescore=80 - i, scored_by="heuristic", cv_hash="h")
        rows.append(row)
    if rows:
        db.upsert_jobs(rows)
    return AppTest.from_file(str(DASHBOARD), default_timeout=60).run()


def test_empty_db_shows_friendly_message(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch)
    assert not at.exception
    assert any("עוד אין משרות" in i.value for i in at.info)


def test_jobs_render_with_kpis(tmp_path, monkeypatch):
    jobs = [Job("greenhouse", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel",
                date_posted="2099-01-01"),
            Job("remotive", "AI Engineer", "Beta", "https://b/1", is_remote=True, remote_region="Worldwide")]
    at = _app(tmp_path, monkeypatch, jobs)
    assert not at.exception
    assert [t.label for t in at.tabs] == ["משרות", "תהליך", "תובנות", "מקורות", "פרופיל"]
    kpis = {m.label: m.value for m in at.metric}
    assert kpis["משרות מתאימות"] == "2" and kpis["הוגשה מועמדות"] == "0"


class _Ok:
    def raise_for_status(self):
        pass


def _launch(at):
    return next(b for b in at.button if "המשרה הבאה" in b.label)


def test_run_button_starts_fixed_pipeline_by_default(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: calls.append(cmd))
    at = _app(tmp_path, monkeypatch)
    assert not [s for s in at.slider if s.key == "agent_goal"]
    _launch(at).click().run()
    assert calls[-1][1:] == ["run_agent.py"]


def test_agent_mode_runs_agent_with_chosen_goal(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr("requests.get", lambda *a, **kw: _Ok())
    at = _app(tmp_path, monkeypatch)
    next(t for t in at.toggle if t.key == "agent_mode").set_value(True).run()
    goal = next(s for s in at.slider if s.key == "agent_goal")
    assert (goal.min, goal.max) == (3, 10) and goal.value == 10      # config goal_matches, clamped
    goal.set_value(4).run()
    _launch(at).click().run()
    assert calls[-1][1:] == ["run_agent.py", "--agent", "--goal", "4"]


def test_agent_mode_blocks_run_when_local_model_server_is_down(tmp_path, monkeypatch):
    import requests

    def down(*a, **kw):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr("requests.get", down)
    at = _app(tmp_path, monkeypatch)
    next(t for t in at.toggle if t.key == "agent_mode").set_value(True).run()
    assert any("LM Studio" in w.value for w in at.warning)
    assert _launch(at).disabled
