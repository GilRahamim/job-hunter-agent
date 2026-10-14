from datetime import date

import pytest

from jobhunter.config import load_config
from jobhunter.filters import (age_ok, filter_jobs, location_ok, region_pattern, role_ok,
                               seniority_ok)
from jobhunter.models import Job

CASES = [
    ("Tel Aviv-Yafo, Tel Aviv District, Israel", "", False, True),
    ("Remote - Worldwide", "", False, True),
    ("Remote (US only)", "", False, False),
    ("Remote, EMEA", "", False, True),
    ("New York, NY", "", False, False),
    ("קריית גת", "", False, True),
    ("", "Anywhere in the World", True, True),
    ("", "USA Only", True, False),
    ("רחובות, M, Israel", "", False, True),
    ("Herzliya", "", False, True),
    ("Remote", "", False, True),
    ("Remote", "USA", True, False),
    ("Remote", "Europe", True, True),
    ("Remote - US or EMEA", "", False, True),
    ("Petah Tikva, IL", "", False, True),
    ("Illinois", "", False, False),
    ("Lodz, Poland", "", False, False),
    ("Remote, EST timezone", "", False, False),
    ("Testing City", "", False, False),
    ("Remote", "United Kingdom, United States", True, False),
    ("London, UK", "", False, False),
    ("Remote - Canada", "", True, False),
]


@pytest.fixture(scope="module")
def cfg():
    return load_config()


@pytest.fixture(scope="module")
def ok(cfg):
    return region_pattern(cfg["filters"]["remote_regions_ok"])


@pytest.mark.parametrize("location,region,is_remote,expected", CASES)
def test_location_cases(ok, location, region, is_remote, expected):
    assert location_ok(location, region, is_remote, ok) is expected


@pytest.mark.parametrize("title,expected", [
    ("Junior Python Developer", True),
    ("AI/ML Engineer", True),
    ("Data Analyst", True),
    ("מפתח/ת Backend", True),
    ("Senior Account Executive", False),       # exclude keyword (and no role keyword)
    ("Software Engineer, Recruiter Tools", False),
    ("Marketing Manager", False),
    ("Office Cleaner", False),
])
def test_role(cfg, title, expected):
    assert role_ok(title, cfg) is expected


@pytest.mark.parametrize("title,expected", [
    ("Senior Backend Developer", False),
    ("Sr. Data Engineer", False),
    ("Team Lead, Platform", False),
    ("Leading Edge Software Engineer", True),     # 'lead' must be a whole word
    ("Software Engineer II", False),             # level II+ asks for experience: junior only
    ("Staff Engineer", False),
    ("מפתח בכיר", False),
    ("Junior Developer", True),
])
def test_seniority(cfg, title, expected):
    assert seniority_ok(title, cfg) is expected


def test_seniority_toggle(cfg):
    off = {**cfg, "filters": {**cfg["filters"], "exclude_senior": False}}
    assert seniority_ok("Senior Developer", off)


def test_age_keeps_undated_and_drops_old():
    today = date(2026, 10, 13)
    assert age_ok(None, 21, today)
    assert age_ok("garbage", 21, today)
    assert age_ok("2026-10-01", 21, today)
    assert not age_ok("2026-09-01", 21, today)
    assert age_ok("2025-01-01", None, today)


def test_filter_jobs_counts_reasons(cfg):
    today = date(2026, 10, 13)
    jobs = [
        Job("t", "Junior Python Developer", "A", "https://a/1", location="Tel Aviv, Israel", date_posted="2026-10-10"),
        Job("t", "Python Developer", "A", "https://a/2", location="Austin, Texas, United States"),
        Job("t", "Office Manager", "A", "https://a/3", location="Tel Aviv, Israel"),
        Job("t", "Senior Python Developer", "A", "https://a/4", location="Tel Aviv, Israel"),
        Job("t", "Python Developer", "A", "https://a/5", location="Tel Aviv, Israel", date_posted="2026-01-01",
            description="Python"),
        Job("t", "Backend Developer", "A", "https://a/6", is_remote=True, remote_region="Worldwide",
            description="Python APIs"),
    ]
    kept, dropped = filter_jobs(jobs, cfg, today)
    assert [j.url for j in kept] == ["https://a/1", "https://a/6"]
    assert dict(dropped) == {"location": 1, "role": 1, "senior": 1, "age": 1}


def test_israel_and_remote_switches(cfg):
    only_remote = {**cfg, "filters": {**cfg["filters"], "israel": False}}
    il = Job("t", "Python Developer", "A", "https://a/1", location="Tel Aviv, Israel")
    kept, dropped = filter_jobs([il], only_remote)
    assert not kept and dropped["location"] == 1


# ---------------------------------------------------------------- junior mode (no experience required)

from jobhunter.filters import experience_ok, required_years  # noqa: E402


def j(title="Python Developer", desc=""):
    return Job("t", title, "A", "https://a/x", location="Tel Aviv, Israel", description=desc)


def test_required_years_parsing():
    assert required_years("3+ years of experience") == 3
    assert required_years("1-2 years") == 1                 # lower bound of a range
    assert required_years("0-1 years, will train") == 0
    assert required_years("דרושים 4 שנות ניסיון") == 4
    assert required_years("no stated requirement") == 0


def test_experience_filter_modes():
    assert experience_ok(j(desc="Python and SQL"), 0)
    assert not experience_ok(j(desc="3+ years of Python experience"), 0)
    assert not experience_ok(j(desc="1-2 years"), 0)
    assert experience_ok(j(desc="1-2 years"), 1)
    assert experience_ok(j(desc="10 years"), None)         # filter off


def test_filter_jobs_drops_with_experience_reason(cfg):
    kept, dropped = filter_jobs([j(desc="Python"), j("Data Analyst", "2+ years experience")], cfg)
    assert [x.title for x in kept] == ["Python Developer"] and dropped["experience"] == 1


def test_experienced_titles_are_dropped(cfg):
    assert not seniority_ok("Experienced Python Developer", cfg)
    assert not seniority_ok("Mid-Level Backend Engineer", cfg)


# ---------------------------------------------------------------- junior-only guardrails

from jobhunter.filters import junior_reason, junior_signals  # noqa: E402


@pytest.mark.parametrize("text,years", [
    ("At least four years of experience in a similar role", 4),
    ("1+ year of experience in C++", 1),
    ("two (2) years of experience", 2),
    ("three or more years of experience", 3),
    ("ניסיון של שנתיים בפיתוח - חובה", 2),
    ("שנת ניסיון לפחות", 1),
    ("The company was founded 10 years ago", 0),
    ("Candidates must be 18 years old", 0),
])
def test_required_years_more_phrasings(text, years):
    assert required_years(text) == years


@pytest.mark.parametrize("title,desc,reason", [
    ("Python Developer", "Python, SQL. Fresh graduates welcome.", None),
    ("Junior Data Engineer", "1-2 years of experience in data engineering", None),  # junior title: up to 1
    ("Junior Data Engineer", "3+ years of experience", "experience"),
    ("Data Analyst", "1+ years of experience with SQL", "experience"),
    ("Embedded Engineer", "Proven experience in embedded C", "experience"),
    ("Software Engineer II", "Python", "senior"),
    ("Backend Platform Team Leader", "Python", "senior"),
    ("Software Engineer", "", "unverified"),            # no description: cannot check experience
    ("Junior Software Engineer", "", None),
    ("סטודנט/ית לפיתוח תוכנה", "", None),
])
def test_junior_reason(cfg, title, desc, reason):
    assert junior_reason(j(title, desc), cfg) == reason


def test_junior_signals_english_and_hebrew(cfg):
    words = cfg["filters"]["junior_keywords"]
    assert junior_signals(j("Graduate Software Engineer", "No experience required"), words) == \
        ["graduate", "no experience"]
    assert "ללא ניסיון" in junior_signals(j("מפתח/ת", "משרה ללא ניסיון לבוגרי תואר"), words)
    assert junior_signals(j("Internal Tools Engineer", "Python"), words) == []   # "intern" is a whole word
