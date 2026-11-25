import copy

import pytest

from jobhunter.collectors import ats, board_search
from jobhunter.collectors.base import CollectorResult
from jobhunter.config import load_config
from jobhunter.models import Job


@pytest.fixture
def cfg():
    c = copy.deepcopy(load_config())
    c["search"]["queries"] = ["Junior Data Analyst"]
    return c


def test_boards_in_reads_every_supported_ats():
    text = " ".join([
        "https://www.comeet.com/jobs/Team8/61.003/junior-dev/9C.D5A",
        "https://job-boards.greenhouse.io/Wiz/jobs/123",
        "https://jobs.lever.co/Riskified/abc",
        "https://jobs.ashbyhq.com/monday.com/xyz",
        "https://jobs.smartrecruiters.com/ElbitSystems/743999",
        "https://boards.greenhouse.io/embed/job_board?for=gongio",
    ])
    assert board_search.boards_in(text) == {
        ("comeet", "team8/61.003"), ("greenhouse", "wiz"), ("lever", "riskified"),
        ("ashby", "monday.com"), ("smartrecruiters", "ElbitSystems"), ("greenhouse", "gongio")}


def test_dork_ors_the_domains_and_adds_the_location(cfg):
    q = board_search.dork("Junior Data Analyst", cfg)
    assert q.startswith("(site:comeet.com/jobs OR site:boards.greenhouse.io")
    assert q.endswith(") Junior Data Analyst israel")


def test_group_dorks_make_one_search_per_role_group(cfg):
    cfg["sources"]["board_search"]["titles_per_group"] = 2
    dorks = board_search.group_dorks(cfg)
    assert len(dorks) == len(cfg["agent"]["role_groups"])
    assert dorks[0].endswith('junior ("AI Engineer" OR "GenAI Engineer") israel')


def test_search_without_a_key_is_skipped_not_an_error(cfg, monkeypatch):
    monkeypatch.setattr(board_search, "load_env", lambda: None)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    result = board_search.collect_board_search(cfg)
    assert result.jobs == [] and result.error is None and "SERPAPI_API_KEY" in result.warning


def test_new_boards_are_read_and_followed_ones_skipped(cfg, monkeypatch):
    monkeypatch.setattr(board_search, "load_env", lambda: None)
    monkeypatch.setenv("SERPAPI_API_KEY", "k")
    monkeypatch.setattr(board_search, "get_json", lambda url, params=None, **kw: {"organic_results": [
        {"link": "https://jobs.lever.co/newco/1"}, {"link": "https://jobs.lever.co/oldco/2"},
        {"link": "https://jobs.ashbyhq.com/deadco/3"}]})
    monkeypatch.setattr(board_search, "followed", lambda config: {("lever", "oldco")})
    fetched = []

    def fetch_lever(entry):
        fetched.append(entry)
        return [Job("lever", "Data Analyst", "NewCo", "https://jobs.lever.co/newco/1")]

    def fetch_ashby(entry):
        raise RuntimeError("404")

    monkeypatch.setitem(ats.FETCHERS, "lever", fetch_lever)
    monkeypatch.setitem(ats.FETCHERS, "ashby", fetch_ashby)
    result = board_search.collect_board_search(cfg)
    assert fetched == ["newco"]                                          # oldco is already followed
    assert [j.company for j in result.jobs] == ["NewCo"]
    assert "deadco" in result.error                                      # a dead board is reported, not raised


def test_board_search_is_never_part_of_the_daily_run(cfg, monkeypatch):
    from jobhunter import collectors
    ran = []
    monkeypatch.setattr(collectors, "_run_one", lambda name, config, limit: (
        ran.append(name) or CollectorResult(name), 0.0))
    for name in collectors._SOURCES:
        cfg["sources"].setdefault(collectors._SOURCES[name][2], {})["enabled"] = True
    collectors.collect_all(cfg)
    assert "board_search" not in ran and "ats" in ran
    ran.clear()
    collectors.collect_all(cfg, ["board_search"])
    assert ran == ["board_search"]
