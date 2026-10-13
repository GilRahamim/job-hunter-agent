"""Remote job boards: Remotive, RemoteOK, Himalayas, WeWorkRemotely (RSS), Arbeitnow."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any, Callable

from jobhunter.collectors.base import (CollectorResult, clean, get_json, get_session, get_text,
                                       html_to_text, to_iso)
from jobhunter.models import Job

log = logging.getLogger(__name__)

REMOTIVE_URL = "https://remotive.com/api/remote-jobs?category={category}"
REMOTIVE_CATEGORIES = ["software-development", "artificial-intelligence", "data", "devops", "qa"]
REMOTEOK_URL = "https://remoteok.com/api"
HIMALAYAS_URL = "https://himalayas.app/jobs/api?limit={size}&offset={offset}"
HIMALAYAS_PAGE_SIZE = 20          # the API caps limit at 20
HIMALAYAS_MAX_PAGES = 10
WWR_URL = "https://weworkremotely.com/categories/{category}.rss"
WWR_CATEGORIES = ["remote-back-end-programming-jobs", "remote-full-stack-programming-jobs",
                  "remote-programming-jobs", "remote-devops-sysadmin-jobs"]
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api?page={page}"
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


# ------------------------------------------------------------ parsers (pure)

def parse_remotive(data: dict) -> list[Job]:
    jobs = [Job(
        source="remotive",
        title=clean(j.get("title")),
        company=clean(j.get("company_name")),
        url=clean(j.get("url")),
        location=clean(j.get("candidate_required_location")),
        description=html_to_text(j.get("description")),
        is_remote=True,
        remote_region=clean(j.get("candidate_required_location")),
        date_posted=to_iso(j.get("publication_date")),
    ) for j in data.get("jobs", [])]
    return [j for j in jobs if j.title and j.url]


def parse_remoteok(data: list) -> list[Job]:
    jobs = []
    for j in data:
        if not isinstance(j, dict) or not j.get("position"):   # first element is a legal notice
            continue
        region = clean(j.get("location"))
        tags = ", ".join(j.get("tags") or [])
        jobs.append(Job(
            source="remoteok",
            title=clean(j.get("position")),
            company=clean(j.get("company")),
            url=clean(j.get("url") or j.get("apply_url")),
            location=region,
            description=(html_to_text(j.get("description")) + (f"\n\nTags: {tags}" if tags else "")).strip(),
            is_remote=True,
            remote_region=region,
            date_posted=to_iso(j.get("date")),
        ))
    return [j for j in jobs if j.url]


def parse_himalayas(data: dict) -> list[Job]:
    jobs = []
    for j in data.get("jobs", []):
        region = ", ".join(clean(x) for x in j.get("locationRestrictions") or [])
        jobs.append(Job(
            source="himalayas",
            title=clean(j.get("title")),
            company=clean(j.get("companyName")),
            url=clean(j.get("applicationLink")),
            location=region or "Worldwide",
            description=html_to_text(j.get("description")) or clean(j.get("excerpt")),
            is_remote=True,
            remote_region=region,                     # empty list = worldwide
            date_posted=to_iso(j.get("pubDate")),
        ))
    return [j for j in jobs if j.title and j.url]


def parse_wwr(xml_text: str) -> list[Job]:
    jobs = []
    for item in ET.fromstring(xml_text).iter("item"):
        raw_title = clean(item.findtext("title"))
        company, sep, title = raw_title.partition(": ")
        if not sep:
            company, title = "", raw_title
        region = clean(item.findtext("region"))
        jobs.append(Job(
            source="weworkremotely",
            title=title,
            company=company,
            url=clean(item.findtext("link")),
            location=region,
            description=html_to_text(item.findtext("description")),
            is_remote=True,
            remote_region=region,
            date_posted=to_iso(item.findtext("pubDate")),
        ))
    return [j for j in jobs if j.title and j.url]


def parse_arbeitnow(data: dict) -> list[Job]:
    jobs = [Job(
        source="arbeitnow",
        title=clean(j.get("title")),
        company=clean(j.get("company_name")),
        url=clean(j.get("url")),
        location=clean(j.get("location")),
        description=html_to_text(j.get("description")),
        is_remote=True,
        remote_region=clean(j.get("location")),
        date_posted=to_iso(j.get("created_at")),
    ) for j in data.get("data", []) if j.get("remote") is True]
    return [j for j in jobs if j.title and j.url]


# ------------------------------------------------------------ fetchers

def _dedupe_by_url(jobs: list[Job]) -> list[Job]:
    return list({j.id: j for j in jobs}.values())


def _remotive() -> list[Job]:
    jobs: list[Job] = []
    for category in REMOTIVE_CATEGORIES:
        jobs.extend(parse_remotive(get_json(REMOTIVE_URL.format(category=category))))
    return _dedupe_by_url(jobs)


def _remoteok() -> list[Job]:
    return parse_remoteok(get_json(REMOTEOK_URL, headers=BROWSER_UA))


def _himalayas() -> list[Job]:
    jobs: list[Job] = []
    for page in range(HIMALAYAS_MAX_PAGES):
        data = get_json(HIMALAYAS_URL.format(size=HIMALAYAS_PAGE_SIZE, offset=page * HIMALAYAS_PAGE_SIZE))
        jobs.extend(parse_himalayas(data))
        if not data.get("jobs"):
            break
    return jobs


def _wwr() -> list[Job]:
    jobs: list[Job] = []
    errors = []
    for category in WWR_CATEGORIES:
        try:
            resp = get_session().get(WWR_URL.format(category=category), timeout=15, allow_redirects=True)
            resp.raise_for_status()
            jobs.extend(parse_wwr(resp.text))
        except Exception as e:  # noqa: BLE001 — keep the other categories
            errors.append(f"{category}({type(e).__name__})")
    if errors and not jobs:
        raise RuntimeError("all categories failed: " + ", ".join(errors))
    return _dedupe_by_url(jobs)


def _arbeitnow() -> list[Job]:
    jobs: list[Job] = []
    for page in (1, 2, 3):
        jobs.extend(parse_arbeitnow(get_json(ARBEITNOW_URL.format(page=page))))
    return jobs


def _collect(name: str, fetch: Callable[[], list[Job]], limit: int | None) -> CollectorResult:
    try:
        jobs = fetch()
        return CollectorResult(name, jobs[:limit] if limit else jobs)
    except Exception as e:  # noqa: BLE001 — never raise out of a collector
        log.warning("%s failed: %s", name, e)
        return CollectorResult(name, error=f"{type(e).__name__}: {str(e)[:120]}")


def collect_remotive(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    return _collect("remotive", _remotive, limit)


def collect_remoteok(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    return _collect("remoteok", _remoteok, limit)


def collect_himalayas(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    return _collect("himalayas", _himalayas, limit)


def collect_weworkremotely(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    return _collect("weworkremotely", _wwr, limit)


def collect_arbeitnow(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    return _collect("arbeitnow", _arbeitnow, limit)
