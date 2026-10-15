from datetime import datetime, timezone
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
    assert "SERPAPI_API_KEY" in res.warning          # enabled but no key: say why it found nothing


def _fake_serpapi(monkeypatch, fixture) -> list[str]:
    """Record the queries sent to SerpAPI; answer each with the sample fixture."""
    sent: list[str] = []
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setattr(serpapi, "load_env", lambda: None)
    monkeypatch.setattr(serpapi, "get_json", lambda url, params: sent.append(params["q"])
                        or fixture("serpapi_sample.json"))
    return sent


def test_serpapi_uses_its_own_query_list(monkeypatch, fixture):
    sent = _fake_serpapi(monkeypatch, fixture)
    config = {"search": {"queries": ["a", "b", "c"]},
              "sources": {"serpapi_google_jobs": {"queries": ["מפתח תוכנה ג'וניור", "Junior QA"]}}}
    res = serpapi.collect_serpapi(config)
    assert sent == ["מפתח תוכנה ג'וניור", "Junior QA"]
    assert res.jobs and res.error is None


def test_serpapi_falls_back_to_search_queries(monkeypatch, fixture):
    sent = _fake_serpapi(monkeypatch, fixture)
    serpapi.collect_serpapi({"search": {"queries": ["a", "b"]}, "sources": {"serpapi_google_jobs": {}}})
    assert sent == ["a", "b"]


def test_serpapi_relative_posted_at():
    now = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
    assert serpapi.posted_at_to_iso("2 days ago", now) == "2026-10-13"
    assert serpapi.posted_at_to_iso("21 hours ago", now) == "2026-10-14"
    assert serpapi.posted_at_to_iso("30+ days ago", now) == "2026-09-15"
    assert serpapi.posted_at_to_iso("1 week ago", now) == "2026-10-08"
    assert serpapi.posted_at_to_iso("1 month ago", now) == "2026-09-15"
    assert serpapi.posted_at_to_iso("Just posted", now) == "2026-10-15"
    assert serpapi.posted_at_to_iso("2026-10-01", now) == "2026-10-01"
    assert serpapi.posted_at_to_iso("full-time", now) is None
    assert serpapi.posted_at_to_iso(None, now) is None


def test_serpapi_jobs_get_a_date(fixture):
    jobs = serpapi.parse_serpapi(fixture("serpapi_sample.json"))
    assert jobs[0].date_posted                       # "2 days ago" in the fixture
    assert jobs[1].date_posted is None               # no posted_at at all


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


# ---------------------------------------------------------------- Workday / Comeet / Lever EU

def test_workday_israel_facet_prefers_the_country(fixture):
    # Nvidia: a country entry under locationHierarchy1 and city entries under locations
    assert ats.israel_facets(fixture("workday_nvidia_search.json")) == \
        {"locationHierarchy1": ["2fcb99c455831013ea52bbe14cf9326c"]}


def test_workday_israel_facet_falls_back_to_cities():
    data = {"facets": [{"facetParameter": "locationMainGroup", "values": [{"facetParameter": "locations", "values": [
        {"descriptor": "Israel, Haifa", "id": "h"}, {"descriptor": "Israel, Jerusalem", "id": "j"},
        {"descriptor": "United States, Oregon", "id": "o"}]}]}]}
    assert ats.israel_facets(data) == {"locations": ["h", "j"]}
    assert ats.israel_facets({"facets": []}) == {}


def test_workday_detail(fixture):
    job = ats.parse_workday_posting(fixture("workday_nvidia_detail.json")["jobPostingInfo"], "nvidia")
    assert_clean([job])
    assert job.source == "workday" and job.company == "Nvidia" and "Israel" in job.location
    assert job.description and job.date_posted


def test_comeet(fixture):
    jobs = ats.parse_comeet(fixture("comeet_drivenets.json"))
    assert_clean(jobs)
    assert all(j.source == "comeet" and j.company and j.description for j in jobs)


def test_comeet_reads_the_token_from_the_careers_page(monkeypatch, fixture):
    seen = {}
    monkeypatch.setattr(ats, "get_text", lambda url, **kw: 'x = {"company_uid": "72.006", "token": "ABCDEF0123456789AB"}')
    monkeypatch.setattr(ats, "get_json", lambda url, **kw: seen.setdefault("url", url) and fixture("comeet_drivenets.json"))
    assert ats.fetch_comeet("drivenets/72.006")
    assert "company/72.006/positions?token=ABCDEF0123456789AB" in seen["url"]


def test_lever_falls_back_to_the_eu_host(monkeypatch, fixture):
    import requests
    calls = []

    def fake(url, **kw):
        calls.append(url)
        if "api.eu.lever.co" not in url:
            resp = requests.Response()
            resp.status_code = 404
            raise requests.HTTPError(response=resp)
        return fixture("lever_cloudinary.json")
    monkeypatch.setattr(ats, "get_json", fake)
    assert ats.fetch_lever("mobileye") and "api.eu.lever.co" in calls[-1]


def test_company_boards_accept_workday_and_comeet_entries(monkeypatch):
    monkeypatch.setitem(ats.FETCHERS, "workday", lambda e: [Job("workday", "Engineer", "Intel", "https://w/1")])
    monkeypatch.setitem(ats.FETCHERS, "comeet", lambda e: (_ for _ in ()).throw(RuntimeError("no token")))
    res = ats.collect_company_boards({}, companies={"workday": [{"tenant": "intel", "wd": "wd1", "site": "External"}],
                                                    "comeet": ["acme/1.001"]})
    assert [j.title for j in res.jobs] == ["Engineer"] and "acme/1.001(RuntimeError" in res.error


# ---------------------------------------------------------------- Tech Map / VC boards / descriptions

def test_techmap(fixture):
    from jobhunter.collectors import techmap
    text = (Path(__file__).parent / "fixtures" / "techmap_software.csv").read_text(encoding="utf-8")
    jobs = techmap.parse_techmap(text)
    assert_clean(jobs)
    assert all(j.source == "techmap" and j.company and j.location.endswith("Israel") for j in jobs)
    assert all(j.description.startswith("Level: ") for j in jobs)


def test_getro_board(fixture):
    from jobhunter.collectors import getro
    jobs = getro.parse_getro(fixture("getro_israelvcforum.json")["results"])
    assert_clean(jobs)
    assert all(j.source == "getro" and j.company for j in jobs)
    assert any(j.description.startswith("Seniority: ") for j in jobs)


def test_getro_pages_until_the_count(monkeypatch, fixture):
    from jobhunter.collectors import getro
    page = fixture("getro_israelvcforum.json")["results"]
    pages = []

    def fake(board_id, n, location="Israel"):
        pages.append(n)
        return {**page, "count": 2 * len(page["jobs"])}
    monkeypatch.setattr(getro, "search_page", fake)
    monkeypatch.setattr(getro, "PAUSE_S", 0)
    assert len(getro.fetch_board(10949)) == 2 * len(page["jobs"]) and pages == [0, 1]


def test_linkedin_job_ids():
    from jobhunter.collectors.details import linkedin_job_id
    assert linkedin_job_id("https://il.linkedin.com/jobs/view/java-developer-at-infinidat-4475696123?utm_source=x") \
        == "4475696123"
    assert linkedin_job_id("https://www.linkedin.com/jobs/view/4475696123") == "4475696123"
    assert linkedin_job_id("https://www.comeet.com/jobs/x/1.002/y/3.004") is None


def test_fill_descriptions_only_reads_jobs_without_one(monkeypatch):
    from jobhunter.collectors import details
    monkeypatch.setattr(details, "fetch_posting", lambda job: details.Posting("3+ years of Java"))
    bare = Job("techmap", "Java Developer", "A", "https://il.linkedin.com/jobs/view/java-at-a-1234567")
    full = Job("techmap", "Python Developer", "B", "https://il.linkedin.com/jobs/view/py-at-b-7654321",
               description="Python, no experience needed")
    other = Job("techmap", "QA", "C", "https://www.comeet.com/jobs/c/1.002/qa/3.004")
    assert details.fill_descriptions([bare, full, other], limit=5, pause=(0, 0)) == set()
    assert bare.description == "3+ years of Java" and full.description.startswith("Python") and not other.description


@pytest.mark.parametrize("name, closed", [("linkedin_job_closed.html", True), ("linkedin_job_open.html", False)])
def test_linkedin_page_tells_if_job_is_closed(name, closed):
    from jobhunter.collectors.details import parse_posting
    posting = parse_posting((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))
    assert posting.closed is closed
    assert "Junior Python Developer" in posting.description and "SQL" in posting.description


def test_fill_descriptions_reports_closed_jobs(monkeypatch):
    from jobhunter.collectors import details
    monkeypatch.setattr(details, "fetch_posting", lambda job: details.Posting("Python", closed=True))
    job = Job("techmap", "Python Developer", "A", "https://il.linkedin.com/jobs/view/py-at-a-1234567")
    assert details.fill_descriptions([job], limit=5, pause=(0, 0)) == {job.id}


def test_jobspy_partial_miss_is_a_warning_not_an_error(monkeypatch):
    import sys, types
    monkeypatch.setitem(sys.modules, "jobspy", types.ModuleType("jobspy"))
    monkeypatch.setattr(jobspy_source.time, "sleep", lambda s: None)
    job = Job("jobspy:linkedin", "Python Developer", "Acme", "https://x/1")
    monkeypatch.setattr(jobspy_source, "_scrape",
                        lambda sites, query, *a: [job] if query == "python" else [])
    cfg = {"sources": {"jobspy": {}}, "search": {"queries": ["python", "nothing here"], "location": "Israel"}}
    r = jobspy_source.collect_jobspy(cfg)
    assert r.error is None and r.warning and len(r.jobs) == 1

    monkeypatch.setattr(jobspy_source, "_scrape", lambda *a: [])
    r = jobspy_source.collect_jobspy(cfg)
    assert r.error and not r.jobs                          # nothing at all is still a failure


def test_jobspy_remote_pass_only_for_whole_word_keywords(monkeypatch):
    import sys
    import types
    monkeypatch.setitem(sys.modules, "jobspy", types.ModuleType("jobspy"))
    monkeypatch.setattr(jobspy_source.time, "sleep", lambda s: None)
    passes = []
    monkeypatch.setattr(jobspy_source, "_scrape",
                        lambda sites, q, cfg, loc, remote, fd: passes.append((q, remote)) or [])
    cfg = {"sources": {"jobspy": {"remote_query_keywords": ["ai", "machine learning"]}},
           "search": {"queries": ["Junior AI Engineer", "Email Marketing", "Machine Learning Intern"],
                      "location": "Israel"}}
    jobspy_source.collect_jobspy(cfg)
    remote = [q for q, r in passes if r]
    assert remote == ["Junior AI Engineer", "Machine Learning Intern"]     # "ai" inside "Email" is not "AI"
