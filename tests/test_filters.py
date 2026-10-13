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
    ("Software Engineer II", True),
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
        Job("t", "Python Developer", "A", "https://a/5", location="Tel Aviv, Israel", date_posted="2026-01-01"),
        Job("t", "Backend Developer", "A", "https://a/6", is_remote=True, remote_region="Worldwide"),
    ]
    kept, dropped = filter_jobs(jobs, cfg, today)
    assert [j.url for j in kept] == ["https://a/1", "https://a/6"]
    assert dict(dropped) == {"location": 1, "role": 1, "senior": 1, "age": 1}


def test_israel_and_remote_switches(cfg):
    only_remote = {**cfg, "filters": {**cfg["filters"], "israel": False}}
    il = Job("t", "Python Developer", "A", "https://a/1", location="Tel Aviv, Israel")
    kept, dropped = filter_jobs([il], only_remote)
    assert not kept and dropped["location"] == 1
