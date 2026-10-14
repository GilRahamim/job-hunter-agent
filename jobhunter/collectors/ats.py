"""Company career boards through public ATS JSON APIs (companies.yaml)."""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

import requests

from jobhunter.collectors.base import (TIMEOUT, CollectorResult, clean, get_json, get_session, get_text,
                                       html_to_text, to_iso)
from jobhunter.config import load_companies
from jobhunter.models import Job

log = logging.getLogger(__name__)

GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
LEVER_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
LEVER_EU_URL = "https://api.eu.lever.co/v0/postings/{slug}?mode=json"     # EU accounts (e.g. Mobileye)
ASHBY_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
SR_LIST_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&offset={offset}"
SR_DETAIL_URL = "https://api.smartrecruiters.com/v1/companies/{slug}/postings/{id}"
WORKDAY_BASE = "https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
WORKDAY_PAGE = 20                 # the API caps `limit` at 20
WORKDAY_MAX_JOBS = 500            # per company; Nvidia has ~420 Israel postings
WORKDAY_WORKERS = 4               # parallel detail calls per company
COMEET_PAGE_URL = "https://www.comeet.com/jobs/{slug}/{uid}"
COMEET_API_URL = "https://www.comeet.co/careers-api/2.0/company/{uid}/positions?token={token}&details=true"
_COMEET_TOKEN = re.compile(r'"token"\s*:\s*"([0-9A-F]{16,64})"')
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


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


def israel_facets(data: dict) -> dict[str, list[str]]:
    """Workday location facet ids for Israel, as {"<facetParameter>": [ids]}.
    The facet name differs per company (locationHierarchy1, locations, Country...) and can be
    nested. A country entry ("Israel") wins over a list of city entries ("Israel, Haifa")."""
    country: dict[str, list[str]] = {}
    cities: dict[str, list[str]] = {}

    def walk(values: list | None, param: str | None) -> None:
        for v in values or []:
            name = (v.get("descriptor") or "").strip().lower()
            if param and v.get("id") and name.startswith("israel"):
                (country if name == "israel" else cities).setdefault(param, []).append(v["id"])
            walk(v.get("values"), v.get("facetParameter") or param)

    for facet in data.get("facets") or []:
        walk(facet.get("values"), facet.get("facetParameter"))
    pick = country or cities
    if not pick:
        return {}
    param = max(pick, key=lambda p: len(pick[p]))       # one facet: mixing facets would AND them
    return {param: pick[param]}


def parse_workday_posting(info: dict, tenant: str) -> Job | None:
    """`jobPostingInfo` from the Workday detail call -> Job."""
    locations = [clean(info.get("location"))] + [clean(x) for x in info.get("additionalLocations") or []]
    location = " / ".join(x for x in locations if x)
    job = Job(
        source="workday",
        title=clean(info.get("title")),
        company=_company_name(tenant),
        url=clean(info.get("externalUrl")),
        location=location,
        description=html_to_text(info.get("jobDescription")),
        is_remote="remote" in location.lower() or clean(info.get("remoteType")).lower() == "remote",
        date_posted=to_iso(info.get("startDate")),
    )
    return job if job.title and job.url else None


def parse_comeet(data: list) -> list[Job]:
    jobs = []
    for p in data:
        loc = p.get("location") or {}
        details = [f"{clean(d.get('name'))}\n{html_to_text(d.get('value'))}" for d in p.get("details") or []]
        if clean(p.get("experience_level")) not in ("", "None"):
            details.append(f"Experience level: {clean(p.get('experience_level'))}")
        jobs.append(Job(
            source="comeet",
            title=clean(p.get("name")),
            company=clean(p.get("company_name")),
            url=clean(p.get("url_active_page")) or clean(p.get("url_comeet_hosted_page")),
            location=clean(loc.get("name")),
            description="\n\n".join(d for d in details if d.strip()),
            is_remote=bool(loc.get("is_remote")) or clean(p.get("workplace_type")).lower() == "remote",
            date_posted=to_iso(p.get("time_updated")),
        ))
    return [j for j in jobs if j.title and j.url]


# ------------------------------------------------------------ fetchers

def fetch_greenhouse(slug: str) -> list[Job]:
    return parse_greenhouse(get_json(GREENHOUSE_URL.format(slug=slug)), slug)


def fetch_lever(slug: str) -> list[Job]:
    try:
        data = get_json(LEVER_URL.format(slug=slug))
    except requests.HTTPError as e:                  # EU accounts answer 404 on the US host
        if e.response is None or e.response.status_code != 404:
            raise
        data = get_json(LEVER_EU_URL.format(slug=slug))
    return parse_lever(data, slug)


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


def _workday_search(base: str, facets: dict, offset: int) -> dict:
    resp = get_session().post(f"{base}/jobs", timeout=TIMEOUT, headers={**BROWSER_UA, "Accept": "application/json"},
                              json={"appliedFacets": facets, "limit": WORKDAY_PAGE, "offset": offset,
                                    "searchText": ""})
    resp.raise_for_status()
    return resp.json()


def fetch_workday(entry: dict) -> list[Job]:
    """Israel postings of one Workday company ({tenant, wd, site} from companies.yaml)."""
    tenant, base = entry["tenant"], WORKDAY_BASE.format(**entry)
    facets = israel_facets(_workday_search(base, {}, 0))
    if not facets:
        raise RuntimeError("no Israel location facet")
    postings: list[dict] = []
    total = None                       # only the first page carries the real total; later pages say 0
    while len(postings) < WORKDAY_MAX_JOBS:
        page = _workday_search(base, facets, len(postings))
        batch = page.get("jobPostings") or []
        postings.extend(batch)
        total = page.get("total") if total is None else total
        if not batch or len(postings) >= (total or 0):
            break

    def detail(path: str) -> Job | None:
        try:
            info = get_json(f"{base}{path}", headers={**BROWSER_UA, "Accept": "application/json"})
            return parse_workday_posting(info.get("jobPostingInfo") or {}, tenant)
        except Exception as e:  # noqa: BLE001 — keep the other postings
            log.warning("workday %s %s detail failed: %s", tenant, path, e)
            return None

    paths = [p["externalPath"] for p in postings if p.get("externalPath")]
    with ThreadPoolExecutor(max_workers=WORKDAY_WORKERS) as pool:     # more gets 403 / timeouts
        return [j for j in pool.map(detail, paths) if j]


def fetch_comeet(entry: str) -> list[Job]:
    """One Comeet company, "<slug>/<uid>" from its careers URL comeet.com/jobs/<slug>/<uid>.
    The API token is public but only published on that page, so it is read there each run."""
    slug, uid = entry.strip("/").split("/")[:2]
    page = get_text(COMEET_PAGE_URL.format(slug=slug, uid=uid), headers=BROWSER_UA)
    match = _COMEET_TOKEN.search(page)
    if not match:
        raise RuntimeError("careers page has no API token")
    return parse_comeet(get_json(COMEET_API_URL.format(uid=uid, token=match.group(1))))


FETCHERS: dict[str, Callable[[Any], list[Job]]] = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
    "comeet": fetch_comeet,
}


# ------------------------------------------------------------ collector

def entry_label(entry: Any) -> str:
    """How a companies.yaml entry is named in errors: the slug, or the Workday tenant."""
    return str(entry["tenant"]) if isinstance(entry, dict) else str(entry)


def _one_company(ats: str, entry: Any) -> tuple[str, str, list[Job], str | None]:
    label = entry_label(entry)
    try:
        return ats, label, FETCHERS[ats](entry), None
    except Exception as e:  # noqa: BLE001 — one dead board must not stop the run
        return ats, label, [], f"{label}({type(e).__name__}: {str(e)[:60]})"


def collect_company_boards(config: dict[str, Any], limit: int | None = None,
                           companies: dict | None = None) -> CollectorResult:
    """Fetch every company in companies.yaml. `limit` caps jobs kept per company."""
    try:
        companies = companies if companies is not None else load_companies()
        tasks = [(ats, entry if isinstance(entry, dict) else str(entry))
                 for ats in FETCHERS for entry in companies.get(ats) or []]
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
