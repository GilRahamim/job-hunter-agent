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
    assert any("עוד אין משרות" in m.value for m in at.markdown)


def test_jobs_render_with_kpis(tmp_path, monkeypatch):
    jobs = [Job("greenhouse", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel",
                date_posted="2099-01-01"),
            Job("remotive", "AI Engineer", "Beta", "https://b/1", is_remote=True, remote_region="Worldwide")]
    at = _app(tmp_path, monkeypatch, jobs)
    assert not at.exception
    assert [t.label for t in at.tabs] == ["משרות", "תהליך", "תובנות", "מקורות", "פרופיל"]
    kpis = {m.label: m.value for m in at.metric}
    assert kpis["משרות מתאימות"] == "2" and kpis["הוגשה מועמדות"] == "0"
