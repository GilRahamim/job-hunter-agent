"""Company career boards through public ATS JSON APIs (companies.yaml)."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from jobhunter.collectors.base import CollectorResult, clean, get_json, html_to_text, to_iso
from jobhunter.config import load_companies
from jobhunter.models import Job

log = logging.getLogger(__name__)

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
SR_LIST_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}"
SR_DETAIL_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}"


def _company_name(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


# ------------------------------------------------------------ parsers (pure)

def parse_greenhouse(data: dict, slug: str) -> list[Job]:
    jobs = []
    for j in data.get("jobs", []):
        location = (j.get("location") or {}).get("name", "")
        jobs.append(Job(
            source="greenhouse",
            title=clean(j.get("title")),
            company=clean(j.get("company_name")) or _company_name(slug),
            url=clean(j.get("absolute_url")),
            location=location,
            description=html_to_text(j.get("content")),
            is_remote="remote" in location.lower(),
            date_posted=to_iso(j.get("first_published") or j.get("updated_at")),
        ))
    return [j for j in jobs if j.title and j.url]


def parse_lever(data: list, slug: str) -> list[Job]:
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        locations = cats.get("allLocations") or [cats.get("location") or ""]
        parts = [clean(j.get("descriptionPlain"))]
        for item in j.get("lists") or []:
            parts.append(f"{clean(item.get('text'))}\n{html_to_text(item.get('content'))}")
        parts.append(clean(j.get("additionalPlain")))
        jobs.append(Job(
            source="lever",
            title=clean(j.get("text")),
            company=_company_name(slug),
            url=clean(j.get("hostedUrl")),
            location=" / ".join(clean(x) for x in locations if x),
            description="\n\n".join(p for p in parts if p),
            is_remote=j.get("workplaceType") == "remote",
            date_posted=to_iso(j.get("createdAt")),
        ))
    return [j for j in jobs if j.title and j.url]


def parse_ashby(data: dict, slug: str) -> list[Job]:
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locations = [clean(j.get("location"))] + [
            clean(s.get("location")) for s in j.get("secondaryLocations") or []]
        jobs.append(Job(
            source="ashby",
            title=clean(j.get("title")),
            company=_company_name(slug),
            url=clean(j.get("jobUrl")),
            location=" / ".join(x for x in locations if x),
            description=clean(j.get("descriptionPlain")),
            is_remote=bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
            date_posted=to_iso(j.get("publishedAt")),
        ))
    return [j for j in jobs if j.title and j.url]


def sr_wanted(item: dict) -> bool:
    """Quick location check so details are fetched only for Israel / remote postings."""
    loc = item.get("location") or {}
    return clean(loc.get("country")).lower() == "il" or bool(loc.get("remote"))


def parse_smartrecruiters_posting(item: dict, detail: dict | None, slug: str) -> Job | None:
    loc = item.get("location") or {}
    sections = ((detail or {}).get("jobAd") or {}).get("sections") or {}
    description = "\n\n".join(
        html_to_text((sections.get(k) or {}).get("text"))
        for k in ("jobDescription", "qualifications", "additionalInformation"))
    url = clean((detail or {}).get("postingUrl")) or \
        f"https://jobs.smartrecruiters.com/{slug}/{item.get('id', '')}"
    job = Job(
        source="smartrecruiters",
        title=clean(item.get("name")),
        company=clean((item.get("company") or {}).get("name")) or _company_name(slug),
        url=url,
        location=clean(loc.get("fullLocation")),
        description=description.strip(),
        is_remote=bool(loc.get("remote")),
        date_posted=to_iso(item.get("releasedDate")),
    )
    return job if job.title and job.url else None


# ------------------------------------------------------------ fetchers

def fetch_greenhouse(slug: str) -> list[Job]:
    return parse_greenhouse(get_json(GREENHOUSE_URL.format(slug=slug)), slug)


def fetch_lever(slug: str) -> list[Job]:
    return parse_lever(get_json(LEVER_URL.format(slug=slug)), slug)


def fetch_ashby(slug: str) -> list[Job]:
    return parse_ashby(get_json(ASHBY_URL.format(slug=slug)), slug)


def fetch_smartrecruiters(slug: str) -> list[Job]:
    items: list[dict] = []
    offset = 0
    while True:
        page = get_json(SR_LIST_URL.format(slug=slug, offset=offset))
        content = page.get("content") or []
        items.extend(content)
        offset += len(content)
        if not content or offset >= page.get("totalFound", 0):
            break
    jobs = []
    for item in (i for i in items if sr_wanted(i)):
        try:
            detail = get_json(SR_DETAIL_URL.format(slug=slug, id=item["id"]))
        except Exception as e:  # noqa: BLE001 — keep the posting without a description
            log.warning("smartrecruiters %s/%s detail failed: %s", slug, item.get("id"), e)
            detail = None
        job = parse_smartrecruiters_posting(item, detail, slug)
        if job:
            jobs.append(job)
    return jobs


FETCHERS: dict[str, Callable[[str], list[Job]]] = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
}


# ------------------------------------------------------------ collector

def _one_company(ats: str, slug: str) -> tuple[str, str, list[Job], str | None]:
    try:
        return ats, slug, FETCHERS[ats](slug), None
    except Exception as e:  # noqa: BLE001 — one dead board must not stop the run
        return ats, slug, [], f"{slug}({type(e).__name__}: {str(e)[:60]})"


def collect_company_boards(config: dict[str, Any], limit: int | None = None,
                           companies: dict | None = None) -> CollectorResult:
    """Fetch every company in companies.yaml. `limit` caps jobs kept per company."""
    try:
        companies = companies if companies is not None else load_companies()
        tasks = [(ats, str(slug)) for ats in FETCHERS for slug in companies.get(ats) or []]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda t: _one_company(*t), tasks))
    except Exception as e:  # noqa: BLE001
        return CollectorResult("ats", error=f"{type(e).__name__}: {e}")

    jobs: list[Job] = []
    failures = []
    for _ats, _slug, found, err in results:
        jobs.extend(found[:limit] if limit else found)
        if err:
            failures.append(err)
    error = f"{len(failures)}/{len(tasks)} companies failed: {', '.join(failures)}" if failures else None
    log.info("ats: %d jobs from %d companies (%d failed)", len(jobs), len(tasks) - len(failures), len(failures))
    return CollectorResult("ats", jobs, error)
