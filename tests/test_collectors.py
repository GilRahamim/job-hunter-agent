from pathlib import Path

import pandas as pd
import pytest

from jobhunter.collectors import SOURCE_NAMES, ats, base, collect_all, jobspy_source, remote_boards, serpapi
from jobhunter.collectors.base import CollectorResult, html_to_text, to_iso
from jobhunter.models import Job

ISO = r"\d{4}-\d{2}-\d{2}"


def assert_clean(jobs: list[Job], *, dated: bool = True):
    assert jobs, "parser returned no jobs"
    for j in jobs:
        assert j.title and j.url
        assert "&lt;" not in j.description and "<p>" not in j.description
        if dated and j.date_posted:
            assert len(j.date_posted) == 10 and j.date_posted[4] == "-"


# ---------------------------------------------------------------- helpers

def test_html_to_text_unescapes_greenhouse_style():
    assert html_to_text("&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;&lt;ul&gt;&lt;li&gt;Python&lt;/li&gt;&lt;/ul&gt;") \
        == "Hello & welcome\n Python"


def test_to_iso_handles_all_shapes():
    assert to_iso("2026-10-13T08:00:00-04:00") == "2026-10-13"
    assert to_iso(1760356800) == "2025-10-13"           # unix seconds
    assert to_iso(1760356800000) == "2025-10-13"        # unix milliseconds
    assert to_iso("Tue, 13 Oct 2026 10:00:00 +0000") == "2026-10-13"
    assert to_iso(None) is None and to_iso("garbage") is None


# ---------------------------------------------------------------- ATS

def test_greenhouse(fixture):
    jobs = ats.parse_greenhouse(fixture("greenhouse_jfrog.json"), "jfrog")
    assert_clean(jobs)
    assert all(j.source == "greenhouse" and j.company for j in jobs)
    assert any(j.description for j in jobs)


def test_lever(fixture):
    jobs = ats.parse_lever(fixture("lever_cloudinary.json"), "cloudinary")
    assert_clean(jobs)
    assert jobs[0].source == "lever" and jobs[0].company == "Cloudinary"


def test_ashby(fixture):
    jobs = ats.parse_ashby(fixture("ashby_moonactive.json"), "moonactive")
    assert_clean(jobs)
    assert jobs[0].source == "ashby"


def test_ashby_skips_unlisted():
    data = {"jobs": [{"title": "Hidden", "jobUrl": "https://x/1", "isListed": False},
                     {"title": "Shown", "jobUrl": "https://x/2", "isListed": True}]}
    assert [j.title for j in ats.parse_ashby(data, "x")] == ["Shown"]


def test_smartrecruiters(fixture):
    data = fixture("smartrecruiters_armis.json")
    item = next(i for i in data["content"] if i["id"] in data["details"])
    job = ats.parse_smartrecruiters_posting(item, data["details"][item["id"]], "armis")
    assert job and job.source == "smartrecruiters" and job.description
    assert "&lt;" not in job.description
    no_detail = ats.parse_smartrecruiters_posting(item, None, "armis")
    assert no_detail and no_detail.url.startswith("https://jobs.smartrecruiters.com/armis/")


# ---------------------------------------------------------------- remote boards

def test_remotive(fixture):
    jobs = remote_boards.parse_remotive(fixture("remotive.json"))
    assert_clean(jobs)
    assert all(j.is_remote for j in jobs)


def test_remoteok_skips_legal_notice(fixture):
    data = fixture("remoteok.json")
    assert "position" not in data[0]
    jobs = remote_boards.parse_remoteok(data)
    assert_clean(jobs)
    assert len(jobs) == len(data) - 1


def test_himalayas_empty_restrictions_means_worldwide(fixture):
    jobs = remote_boards.parse_himalayas(fixture("himalayas.json"))
    assert_clean(jobs)
    data = {"jobs": [{"title": "T", "applicationLink": "https://h/1", "companyName": "C",
                      "locationRestrictions": [], "pubDate": 1760356800}]}
    j = remote_boards.parse_himalayas(data)[0]
    assert j.remote_region == "" and j.location == "Worldwide" and j.date_posted == "2025-10-13"


def test_wwr(fixture):
    jobs = remote_boards.parse_wwr(fixture("wwr_backend.rss"))
    assert_clean(jobs)
    assert all(j.company and j.source == "weworkremotely" for j in jobs)


def test_arbeitnow_keeps_remote_only(fixture):
    jobs = remote_boards.parse_arbeitnow(fixture("arbeitnow.json"))
    assert_clean(jobs)
    mixed = {"data": [{"title": "A", "url": "https://a/1", "remote": False},
                      {"title": "B", "url": "https://a/2", "remote": True}]}
    assert [j.title for j in remote_boards.parse_arbeitnow(mixed)] == ["B"]


def test_serpapi_prefers_apply_link(fixture):
    jobs = serpapi.parse_serpapi(fixture("serpapi_sample.json"))
    assert_clean(jobs)
    assert jobs[0].url == "https://acme.example/jobs/1"
    assert jobs[1].url.startswith("https://www.google.com/")      # falls back to share_link
    assert jobs[1].is_remote


def test_serpapi_skipped_without_key(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setattr(serpapi, "load_env", lambda: None)
    res = serpapi.collect_serpapi({"search": {"queries": ["x"]}})
    assert res.jobs == [] and res.error is None


# ---------------------------------------------------------------- JobSpy

def test_jobspy_frame_to_jobs(fixture):
    df = pd.read_csv(Path(__file__).parent / "fixtures" / "jobspy_sample.csv")
    jobs = jobspy_source.frame_to_jobs(df)
    assert_clean(jobs)
    assert all(j.source.startswith("jobspy:") for j in jobs)


def test_jobspy_frame_handles_nan_and_prefers_direct_url():
    df = pd.DataFrame([{"site": "indeed", "title": "Dev", "company": float("nan"),
                        "job_url": "https://indeed/1", "job_url_direct": "https://co/1",
                        "location": "Haifa", "description": float("nan"),
                        "date_posted": float("nan"), "is_remote": float("nan")}])
    j = jobspy_source.frame_to_jobs(df)[0]
    assert j.url == "https://co/1" and j.company == "" and j.description == ""
    assert j.date_posted is None and j.is_remote is False


# ---------------------------------------------------------------- never raise

def _boom(*a, **k):
    raise ConnectionError("network down")


def test_company_failure_is_reported_not_raised(monkeypatch, fixture):
    def fake_get_json(url, **kw):
        if "greenhouse" in url and "good" in url:
            return fixture("greenhouse_jfrog.json")
        raise TimeoutError("timeout")
    monkeypatch.setattr(ats, "get_json", fake_get_json)
    res = ats.collect_company_boards({}, companies={"greenhouse": ["good", "bad"], "lever": ["bad2"]})
    assert res.jobs and "2/3 companies failed" in res.error


def test_limit_is_per_company(monkeypatch, fixture):
    monkeypatch.setattr(ats, "get_json", lambda url, **kw: fixture("greenhouse_jfrog.json"))
    res = ats.collect_company_boards({}, limit=2, companies={"greenhouse": ["a", "b"]})
    assert len(res.jobs) == 4


@pytest.mark.parametrize("fn", [remote_boards.collect_remotive, remote_boards.collect_remoteok,
                                remote_boards.collect_himalayas, remote_boards.collect_arbeitnow,
                                remote_boards.collect_weworkremotely])
def test_remote_collectors_swallow_errors(monkeypatch, fn):
    monkeypatch.setattr(remote_boards, "get_json", _boom)
    monkeypatch.setattr(remote_boards, "get_session", _boom)
    res = fn({})
    assert res.jobs == [] and "ConnectionError" in (res.error or "") or "failed" in (res.error or "")


def test_collect_all_isolates_crashes(monkeypatch):
    import jobhunter.collectors as c

    def good(config, limit=None):
        return CollectorResult("good", [Job("x", "T", "C", "https://x/1")])

    monkeypatch.setattr(c, "_load", lambda name: _boom if name == "remotive" else good)
    results, health = collect_all({}, only=["remotive", "remoteok"])
    by_source = {h["source"]: h for h in health}
    assert by_source["remotive"]["error"] and by_source["good"]["fetched"] == 1


def test_collect_all_respects_enabled_flags_and_rejects_unknown(monkeypatch):
    import jobhunter.collectors as c
    called = []
    monkeypatch.setattr(c, "_load", lambda name: (lambda config, limit=None: called.append(name) or CollectorResult(name)))
    collect_all({"sources": {"remotive": {"enabled": True}, "remoteok": {"enabled": False}}})
    assert called == ["remotive"]
    with pytest.raises(ValueError):
        collect_all({}, only=["nope"])
    assert "ats" in SOURCE_NAMES
