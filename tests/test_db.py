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
