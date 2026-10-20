import copy

import pytest

from jobhunter import agent, db, stop
from jobhunter.collectors.base import CollectorResult
from jobhunter.config import ROOT, data_dir, load_config, run_dir, user_root
from jobhunter.filters import filter_jobs
from jobhunter.models import CandidateProfile, Job
from jobhunter.personalize import personalize, role_words
from jobhunter.users import UserError, create_user, display_name, list_users, save_cv, slugify

CV = b"Dana Levi\nDigital Marketing Specialist\nSEO, Google Ads, content, Excel\n"


# ---------------------------------------------------------------- users and paths

def test_owner_paths_are_unchanged(monkeypatch):
    monkeypatch.delenv("JOBHUNTER_RUN_DIR")
    monkeypatch.delenv("JOBHUNTER_DB", raising=False)
    assert user_root("") == ROOT and data_dir("") == ROOT / "data" and run_dir("") == ROOT / "data"
    assert db.db_path() == ROOT / "data" / "jobs.db"
    assert load_config("")["profile"]["cv_dir"] == "cv"


def test_create_user_from_cv(tmp_path):
    user = create_user("Dana Levi", "dana.pdf", CV, ["Marketing Specialist", " "])
    assert user == "dana-levi" and list_users() == ["dana-levi"]
    root = tmp_path / "users" / "dana-levi"
    assert (root / "cv" / "dana.pdf").read_bytes() == CV
    cfg = load_config(user)
    assert cfg["auto_from_cv"] is True and cfg["search"]["queries"] == ["Marketing Specialist"]
    assert cfg["profile"]["cv_dir"] == str(root / "cv")
    assert cfg["filters"]["israel"] is True                       # everything else from config.yaml
    assert display_name(user) == "Dana Levi"
    assert db.db_path(user=user) == root / "data" / "jobs.db" and run_dir(user) == root / "data"


def test_user_ids_are_ascii_and_unique():
    assert slugify("דנה") == "" and slugify("Dana  Levi!") == "dana-levi"
    first = create_user("דנה", "cv.docx", CV)
    second = create_user("דנה", "cv.docx", CV)
    assert (first, second) == ("user", "user-2")
    assert display_name(first) == "דנה"


def test_bad_uploads_are_refused_without_creating_a_user():
    with pytest.raises(UserError):
        create_user("Dana", "photo.png", CV)
    with pytest.raises(UserError):
        create_user("Dana", "cv.pdf", b"")
    with pytest.raises(UserError):
        create_user("  ", "cv.pdf", CV)
    assert list_users() == []


def test_save_cv_replaces_by_being_newest(tmp_path):
    user = create_user("Dana", "old.txt", CV)
    path = save_cv(user, "../../new.txt", b"new cv")
    assert path.parent == tmp_path / "users" / user / "cv"          # no path tricks in the file name
    from jobhunter.cv import find_cv
    assert find_cv(load_config(user)["profile"]["cv_dir"]).name == "new.txt"


def test_env_user_drives_db_and_stop_flag(tmp_path, monkeypatch):
    user = create_user("Dana", "cv.txt", CV)
    monkeypatch.setenv("JOBHUNTER_USER", user)
    assert db.db_path() == tmp_path / "users" / user / "data" / "jobs.db"
    stop.request_stop()
    assert stop.stop_requested() and not stop.stop_requested("")      # the owner's run is not stopped


# ---------------------------------------------------------------- personalize

MARKETER = CandidateProfile(seniority="mid", years_experience=4.5, skills=["SEO"],
                            target_roles=["Digital Marketing Specialist", "Content Marketing Manager",
                                          "SEO Specialist"])


def test_role_words_skip_seniority_and_pad_short_words():
    assert role_words(["Junior UX Writer", "Senior Data Analyst"]) == [" ux ", "writer", "data", "analyst"]


def test_personalize_is_a_no_op_for_the_owner():
    cfg = load_config("")
    assert personalize(cfg, MARKETER) is cfg


def test_personalize_derives_search_from_the_cv():
    cfg = copy.deepcopy(load_config(""))
    cfg.update(auto_from_cv=True)
    cfg["search"]["queries"] = []
    out = personalize(cfg, MARKETER)
    f = out["filters"]
    assert out["search"]["queries"] == MARKETER.target_roles
    assert "marketing" in f["role_keywords"] and "marketing" not in f["exclude_keywords"]
    assert "manager" not in f["senior_keywords"] and "senior" in f["senior_keywords"]
    assert f["exclude_senior"] is False and f["max_required_years"] == 7      # ceil(4.5) + 2
    assert f["experienced_phrases"] == [] and f["role_description_keywords"] == []
    assert out["search"]["employers"] == {} and out["profile"]["preferences"] == ""   # owner-only
    assert cfg["search"]["queries"] == []                                     # input not mutated

    jobs = [Job("greenhouse", "Performance Marketing Manager", "Acme", "https://a/1", location="Tel Aviv",
                description="4 years of experience with Google Ads"),
            Job("greenhouse", "Junior Python Developer", "Acme", "https://a/2", location="Tel Aviv"),
            Job("greenhouse", "Marketing Lead", "Acme", "https://a/3", location="Haifa",
                description="10+ years of experience")]
    kept, dropped = filter_jobs(jobs, out)
    assert [j.title for j in kept] == ["Performance Marketing Manager"]
    assert dropped == {"role": 1, "experience": 1}


def test_personalize_keeps_typed_titles_and_junior_limits():
    cfg = copy.deepcopy(load_config(""))
    cfg.update(auto_from_cv=True)
    cfg["search"]["queries"] = ["Graphic Designer"]
    junior = CandidateProfile(seniority="junior", target_roles=["Art Director"])
    out = personalize(cfg, junior)
    assert out["search"]["queries"] == ["Graphic Designer"]
    assert out["filters"]["exclude_senior"] is True and out["filters"]["max_required_years"] == 2


def test_personalize_without_any_titles_keeps_the_config():
    cfg = copy.deepcopy(load_config(""))
    cfg.update(auto_from_cv=True)
    cfg["search"]["queries"] = []
    assert personalize(cfg, CandidateProfile()) is cfg


# ---------------------------------------------------------------- a run for a named user

def test_pipeline_run_for_a_user_uses_their_cv_db_and_titles(tmp_path, monkeypatch):
    user = create_user("Dana", "cv.txt", CV, ["Marketing Specialist"])
    monkeypatch.setenv("JOBHUNTER_USER", user)
    seen = {}

    def fake_collect(config, only=None, limit=None):
        seen["queries"] = list(config["search"]["queries"])
        found = [Job("greenhouse", "Marketing Specialist", "Acme", "https://a/1", location="Tel Aviv, Israel",
                     description="SEO and Google Ads"),
                 Job("greenhouse", "Junior Python Developer", "Beta", "https://b/1", location="Tel Aviv, Israel")]
        return [CollectorResult("ats", found)], [{"source": "ats", "fetched": 2, "error": None, "duration_s": 0}]

    monkeypatch.setattr(agent, "collect_all", fake_collect)
    monkeypatch.setattr(agent, "get_llm", lambda cfg: None)
    state = agent.run(load_config(), no_llm=True)
    assert seen["queries"] == ["Marketing Specialist"]
    saved = db.all_jobs()                                   # the user's DB, from JOBHUNTER_USER
    assert [j["title"] for j in saved] == ["Marketing Specialist"]
    assert db.db_path() == tmp_path / "users" / user / "data" / "jobs.db"
    assert state["stats"]["filtered_by_reason"] == {"role": 1}
