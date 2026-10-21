import pytest

from jobhunter import db
from jobhunter.models import Job


@pytest.fixture
def path(tmp_path):
    return tmp_path / "jobs.db"


def make_row(**extra) -> dict:
    row = Job("greenhouse", "Python Developer", "Acme Ltd", "https://x.com/j/1?utm_source=a").to_dict()
    row.update(extra)
    return row


def get(path, job_id):
    return next(j for j in db.all_jobs(path=path) if j["id"] == job_id)


def test_reupsert_with_new_score_keeps_status_and_notes(path):
    row = make_row()
    db.upsert_jobs([row], path)
    db.update_status(row["id"], "applied", "sent CV on Monday", path)

    db.upsert_jobs([{**row, "score": 88, "prescore": 40, "scored_by": "llm:x",
                     "matching_skills": ["Python", "פייתון"]}], path)
    db.upsert_jobs([row], path)  # plain re-collection afterwards

    job = get(path, row["id"])
    assert job["status"] == "applied"
    assert job["notes"] == "sent CV on Monday"
    assert job["status_updated"]
    assert job["score"] == 88  # collection-only row must not wipe the score
    assert job["matching_skills"] == ["Python", "פייתון"]


def test_first_seen_kept_last_seen_refreshed(path):
    row = make_row()
    db.upsert_jobs([row], path)
    first = get(path, row["id"])
    db.touch_seen([row["id"]], path)
    again = get(path, row["id"])
    assert again["first_seen"] == first["first_seen"]
    assert again["last_seen"] >= first["last_seen"]


def test_id_ignores_tracking_params_and_dedupe_key_normalizes():
    a = Job("lever", "Dev", "Acme Ltd", "https://x.com/j/1?utm_source=a&trk=b")
    b = Job("jobspy:linkedin", "Dev", "ACME Inc.", "https://X.com/j/1")
    assert a.id == b.id
    assert a.dedupe_key == b.dedupe_key == "acme|dev"


def test_existing_ids_and_keys(path):
    row = make_row()
    db.upsert_jobs([row], path)
    ids, keys = db.existing_ids_and_keys(path)
    assert row["id"] in ids and row["dedupe_key"] in keys


def test_update_status_rejects_unknown(path):
    with pytest.raises(ValueError):
        db.update_status("x", "bogus", path=path)


def test_rescore_selection_skips_hidden_and_current(path):
    rows = [Job("greenhouse", f"Dev {i}", "A", f"https://x.com/{i}").to_dict() for i in range(4)]
    for r, h in zip(rows, ["old", "old", "old", "new"]):
        r["cv_hash"] = h
        r["prescore"] = 10
    db.upsert_jobs(rows, path)
    db.update_status(rows[1]["id"], "not_relevant", path=path)
    db.update_status(rows[2]["id"], "applied", path=path)
    ids = {j["id"] for j in db.jobs_needing_rescore("new", 10, path)}
    assert ids == {rows[0]["id"], rows[2]["id"]}


def test_run_and_health(path):
    run_id = db.start_run(path)
    db.finish_run(run_id, {"collected": 5}, [{"source": "ats", "fetched": 5, "duration_s": 1.2},
                                              {"source": "jobspy", "error": "blocked"}], path)
    assert db.last_runs(1, path)[0]["stats"] == {"collected": 5}
    health = db.health_for_run(run_id, path)
    assert {h["source"] for h in health} == {"ats", "jobspy"}


def test_profile_roundtrip(path):
    assert db.load_profile("h1", path) is None
    db.save_profile("h1", "cv.pdf", {"name": "גיל", "skills": ["Python"]}, path)
    assert db.load_profile("h1", path)["name"] == "גיל"
    assert db.latest_profile(path)["cv_file"] == "cv.pdf"


def test_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNTER_DB", str(tmp_path / "env.db"))
    db.upsert_jobs([make_row()])
    assert (tmp_path / "env.db").exists()


def test_backfill_required_years(path):
    old = make_row(title="Dev", description="We need 3+ years of Python")
    db.upsert_jobs([old], path)
    assert db.all_jobs(path=path)[0]["required_years"] is None
    assert db.backfill_required_years(path) == 1
    assert db.all_jobs(path=path)[0]["required_years"] == 3
    assert db.backfill_required_years(path) == 0           # nothing left to fill


def test_status_examples_are_the_users_latest_choices(path):
    rows = [Job("greenhouse", t, c, f"https://x/{i}").to_dict()
            for i, (t, c) in enumerate([("Data Analyst", "A"), ("QA Tester", "B"), ("ML Engineer", "C"),
                                        ("Sales Rep", ""), ("Backend Dev", "E")])]
    db.upsert_jobs(rows, path)
    for row, status in zip(rows, ["interested", "applied", "rejected", "not_relevant", "new"]):
        db.update_status(row["id"], status, path=path)
    got = db.status_examples(5, path)
    assert got == {"liked": ["QA Tester @ B", "Data Analyst @ A"], "disliked": ["Sales Rep"]}
    assert db.status_examples(1, path)["liked"] == ["QA Tester @ B"]          # newest first
    assert db.status_examples(0, path) == {"liked": [], "disliked": []}       # off


def test_experience_report_names_how_each_job_got_in(path):
    import importlib.util
    from pathlib import Path as P
    from jobhunter.config import load_config
    from jobhunter.models import Job
    spec = importlib.util.spec_from_file_location(
        "experience_report", P(__file__).parent.parent / "scripts" / "experience_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    db.upsert_jobs([
        {**Job("greenhouse", "Python Developer", "Rules", "https://r/1",
               description="3+ years of Python").to_dict(), "scored_by": "heuristic"},
        {**Job("jobspy:linkedin", "Python Developer", "Llm", "https://l/1",
               description="Python, a few years in production").to_dict(),
         "required_years": 4, "scored_by": "llm:x"},
        {**Job("greenhouse", "Python Developer", "Fine", "https://f/1",
               description="Python, no experience").to_dict(), "required_years": 0},
    ], path)
    rows = {r["company"]: r for r in mod.report(load_config(), path)}
    assert set(rows) == {"Rules", "Llm"}
    assert (rows["Rules"]["found_by"], rows["Rules"]["years"]) == ("rules", 3)
    assert (rows["Llm"]["found_by"], rows["Llm"]["years"], rows["Llm"]["source"]) == ("llm", 4, "jobspy:linkedin")


def test_agent_report_compares_picks_with_what_the_user_did(path):
    import importlib.util
    from pathlib import Path as P
    from jobhunter.config import load_config
    spec = importlib.util.spec_from_file_location(
        "agent_report", P(__file__).parent.parent / "scripts" / "agent_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cfg = load_config()
    cfg["agent"].update(min_match_score=70, role_groups={"Data": ["Data Analyst"], "Software": ["Python Developer"]})
    jobs = [  # (title, scored_by, score, status)
        ("Junior Data Analyst", "agent:q", 80, "applied"),
        ("Data Analyst", "agent:q", 75, "not_relevant"),
        ("Junior Python Developer", "agent:q", 72, "rejected"),        # applied; the company said no
        ("Python Developer", "agent:q", 50, "new"),
        ("Python Developer", "llm:h", 85, "not_relevant"),
        ("Product Manager", "heuristic", 30, "new"),
    ]
    db.upsert_jobs([{**Job("x", t, f"Co{i}", f"https://j/{i}").to_dict(), "scored_by": by, "score": s}
                    for i, (t, by, s, _) in enumerate(jobs)], path)
    for i, (*_, status) in enumerate(jobs):
        if status != "new":
            db.update_status(Job("x", "", "", f"https://j/{i}").id, status, None, path)
    sections = mod.report(cfg, path)
    picker = dict(sections["picker"])
    assert list(picker) == ["agent", "regular", "heuristic"]
    assert picker["agent"] == {"jobs": 4, "pursued": 2, "dismissed": 1, "open": 1, "judged": 3,
                               "precision": 2 / 3}
    assert picker["regular"]["precision"] == 0 and picker["heuristic"]["precision"] is None
    band = dict(sections["band"])
    assert band["agent >= 70"]["jobs"] == 3 and band["agent < 70"]["open"] == 1
    group = dict(sections["group"])
    assert group["Software"]["precision"] == 1 and group["Data"]["precision"] == 0.5
    assert [k for k, _ in sections["group"]] == ["Software", "Data"]
    assert mod.report(cfg, path, since="2999-01-01")["picker"] == []
