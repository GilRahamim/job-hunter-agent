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
        row["description"] = row["description"] or "Python and SQL."   # else hidden as "unverified"
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
    assert kpis["משרות מתאימות"] == "2" and kpis["קו״ח נשלחו"] == "0"


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


def test_agent_mode_checks_the_vllm_server_when_it_serves_the_agent(tmp_path, monkeypatch):
    import requests
    asked = []

    def down(url, *a, **kw):
        asked.append(url)
        raise requests.ConnectionError("refused")

    monkeypatch.setenv("JOBHUNTER_CONFIG", "config.vllm.yaml")
    monkeypatch.setattr("requests.get", down)
    at = _app(tmp_path, monkeypatch)
    next(t for t in at.toggle if t.key == "agent_mode").set_value(True).run()
    assert "http://127.0.0.1:8000/v1/models" in asked and any("vLLM" in w.value for w in at.warning)
    assert _launch(at).disabled


JOBS = [Job("greenhouse", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel",
            date_posted="2099-01-01")]


def test_sidebar_settings_are_written_to_the_url(tmp_path, monkeypatch):
    monkeypatch.setattr("requests.get", lambda *a, **kw: _Ok())
    at = _app(tmp_path, monkeypatch, JOBS)
    at.slider(key="min_score").set_value(75).run()
    at.toggle(key="agent_mode").set_value(True).run()
    at.slider(key="agent_goal").set_value(4).run()
    assert not at.exception
    qp = {k: (v[0] if isinstance(v, list) else v) for k, v in at.query_params.items()}
    assert qp["min_score"] == "75" and qp["agent_mode"] == "1" and qp["agent_goal"] == "4"
    assert "days" not in at.query_params                       # defaults stay out of the URL


def test_sidebar_settings_are_restored_from_the_url(tmp_path, monkeypatch):
    """A reload (e.g. the theme switch) keeps filters and the run mode."""
    monkeypatch.setattr("requests.get", lambda *a, **kw: _Ok())
    st.cache_data.clear()
    monkeypatch.setenv("JOBHUNTER_DB", str(tmp_path / "jobs.db"))
    row = JOBS[0].to_dict()
    row.update(score=80, prescore=80, scored_by="heuristic", cv_hash="h")
    db.upsert_jobs([row])
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60)
    at.query_params.update(min_score="75", agent_mode="1", agent_goal="5", only_new="1", where="ישראל",
                           stages=["-"])
    at.run()
    assert not at.exception
    assert at.slider(key="min_score").value == 75 and at.slider(key="agent_goal").value == 5
    assert at.toggle(key="only_new").value is True and at.toggle(key="agent_mode").value is True
    assert at.session_state["stages"] == [] and at.session_state["where"] == "ישראל"


def test_bad_url_values_fall_back_to_valid_ones(tmp_path, monkeypatch):
    st.cache_data.clear()
    monkeypatch.setenv("JOBHUNTER_DB", str(tmp_path / "jobs.db"))
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60)
    at.query_params.update(min_score="abc", agent_goal="99", agent_mode="1", where="Mars")
    monkeypatch.setattr("requests.get", lambda *a, **kw: _Ok())
    at.run()
    assert not at.exception
    assert at.slider(key="agent_goal").value == 10


def test_controls_do_not_live_in_the_polling_fragment():
    src = DASHBOARD.read_text(encoding="utf-8")
    poll = src.split("@st.fragment(run_every=3)")[1].split("\ndef ", 2)[1]
    assert "st.toggle" not in poll and "st.slider" not in poll and "st.button" not in poll


def test_stop_toggle_asks_the_running_search_to_stop(tmp_path, monkeypatch):
    from jobhunter import stop
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: None)
    at = _app(tmp_path, monkeypatch)
    assert not [t for t in at.toggle if t.key == "stop_search"]          # only while a run is going
    _launch(at).click().run()
    toggle = next(t for t in at.toggle if t.key == "stop_search")
    toggle.set_value(True).run()
    assert not at.exception and stop.stop_requested()
    next(t for t in at.toggle if t.key == "stop_search").set_value(False).run()
    assert not stop.stop_requested()                                    # switched back off


def test_sent_cv_button_marks_the_job_applied_and_undo_reverts(tmp_path, monkeypatch):
    job = Job("greenhouse", "Junior Python Developer", "Acme", "https://a/1", location="Tel Aviv, Israel")
    at = _app(tmp_path, monkeypatch, [job])
    next(b for b in at.button if b.label == "שלחתי קורות חיים").click().run()
    saved = db.job_detail(job.id)
    assert not at.exception and saved["status"] == "applied" and saved["status_updated"]
    assert any("קו״ח נשלחו ב־" in h.proto.body for h in at.get("html"))
    assert {m.label: m.value for m in at.metric}["קו״ח נשלחו"] == "1"
    next(b for b in at.button if b.label == "בטל סימון שליחה").click().run()
    assert db.job_detail(job.id)["status"] == "interested"


def test_sent_checkbox_in_the_table():
    import ast

    import pandas as pd
    # dashboard.py runs the app when imported, so load just this one function from its source
    tree = ast.parse(DASHBOARD.read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "table_changes")
    ns = {"HE_STATUS": {"חדש": "new", "ראיון": "interview"}, "UNSENT": "interested", "pd": pd}
    exec(compile(ast.Module([fn], []), "dashboard.py", "exec"), ns)
    table = pd.DataFrame({"status_he": ["חדש", "חדש", "חדש"], "sent": [False, False, True]}, index=["a", "b", "c"])
    edited = table.copy()
    edited.loc["a", "sent"] = True                          # ticked -> applied
    edited.loc["b", "status_he"] = "ראיון"                  # status picked -> that status
    edited.loc["c", "sent"] = False                         # unticked -> interested
    assert ns["table_changes"](table, edited) == {"a": "applied", "b": "interview", "c": "interested"}


# ---------------------------------------------------------------- several users

def _two_users(tmp_path, monkeypatch):
    """The owner with one job and a user created from a CV with two jobs of their own."""
    from jobhunter.users import create_user

    st.cache_data.clear()
    monkeypatch.setenv("JOBHUNTER_DB", str(tmp_path / "jobs.db"))
    owner = JOBS[0].to_dict()
    owner.update(score=80, prescore=80, scored_by="heuristic", cv_hash="h", description="Python")
    db.upsert_jobs([owner])
    user = create_user("Dana", "cv.txt", b"Dana\nMarketing Specialist\n", ["Marketing Specialist"])
    rows = []
    for i, title in enumerate(["Marketing Specialist", "Content Marketing Specialist"]):
        row = Job("greenhouse", title, "Acme", f"https://m/{i}", location="Tel Aviv, Israel",
                  description="SEO").to_dict()
        row.update(score=70 - i, prescore=70 - i, scored_by="heuristic", cv_hash="h")
        rows.append(row)
    db.upsert_jobs(rows, db.db_path(user=user))
    return user


def test_user_picker_shows_each_users_own_jobs_and_runs(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.Popen", lambda cmd, **kw: calls.append(cmd))
    user = _two_users(tmp_path, monkeypatch)
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60).run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["משרות מתאימות"] == "1"        # the owner's view
    assert at.selectbox(key="user").options == ["המשתמש הראשי", "Dana"]
    at.selectbox(key="user").set_value(user).run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["משרות מתאימות"] == "2"        # Dana's own DB
    assert at.query_params["user"] in (user, [user])
    assert not [t for t in at.toggle if t.key == "agent_mode"]     # the agent loop is the owner's
    _launch(at).click().run()
    assert calls[-1][1:] == ["run_agent.py", "--user", user]


def test_user_is_restored_from_the_url_and_unknown_users_fall_back(tmp_path, monkeypatch):
    user = _two_users(tmp_path, monkeypatch)
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60)
    at.query_params["user"] = user
    at.run()
    assert at.selectbox(key="user").value == user
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60)
    at.query_params["user"] = "nobody"
    at.run()
    assert not at.exception and at.selectbox(key="user").value == ""


def test_profile_tab_offers_cv_upload_and_add_user(tmp_path, monkeypatch):
    at = _app(tmp_path, monkeypatch, JOBS)
    buttons = [b.label for b in at.get("form_submit_button")] if at.get("form_submit_button") else []
    assert not at.exception
    assert "שמירת קורות החיים" in buttons and "יצירת חיפוש" in buttons


# ---------------------------------------------------------------- Claude handoff

def test_claude_panel_prepares_a_brief_and_lists_claudes_files(tmp_path, monkeypatch):
    from jobhunter import handoff

    at = _app(tmp_path, monkeypatch, JOBS)
    assert not at.exception
    next(b for b in at.button if b.label == "הכנת תיק למשרה").click().run()
    assert not at.exception
    brief = handoff.job_folder(db.job_detail(JOBS[0].id), tmp_path / "jobs.db") / handoff.BRIEF
    assert brief.exists() and "Junior Python Developer" in brief.read_text(encoding="utf-8")
    assert any('claude "Read' in c.value for c in at.code)
    (brief.parent / "cover_letter.md").write_text("Dear Acme", encoding="utf-8")
    at.run()
    assert any(b.label == "עדכון התיק" for b in at.button)
    assert "cover_letter.md" in [d.proto.label for d in at.get("download_button")]


def test_experience_toggle_follows_each_users_cv(tmp_path, monkeypatch):
    user = _two_users(tmp_path, monkeypatch)
    at = AppTest.from_file(str(DASHBOARD), default_timeout=60).run()
    assert at.toggle(key="junior").label == "רק משרות ללא דרישת ניסיון"         # the owner's config
    assert at.toggle(key="junior").value is True                                # on by default
    profile = {"seniority": "mid", "years_experience": 4.5, "target_roles": ["Marketing Specialist"]}
    db.save_profile("h", "cv.txt", profile, db.db_path(user=user))
    at.selectbox(key="user").set_value(user).run()
    assert not at.exception and at.toggle(key="junior").label == "רק משרות עד 7 שנות ניסיון"
    db.save_profile("h2", "cv.txt", {**profile, "seniority": "senior"}, db.db_path(user=user))
    st.cache_data.clear()
    at.run()
    assert not at.exception and not [t for t in at.toggle if t.key == "junior"]  # no limit, no toggle
