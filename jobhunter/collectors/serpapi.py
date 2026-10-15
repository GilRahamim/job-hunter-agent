"""Google Jobs through SerpAPI (optional; skipped without SERPAPI_API_KEY).

Google Jobs indexes AllJobs, Drushim, JobMaster and companies' own pages, so this is how their
postings reach us. Every query is one paid SerpAPI search, so the source has its own short query
list (`sources.serpapi_google_jobs.queries`); without one it falls back to `search.queries`."""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jobhunter.collectors.base import CollectorResult, clean, get_json, to_iso
from jobhunter.config import load_env
from jobhunter.models import Job

log = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"
_AGO = re.compile(r"(\d+)\+?\s*(minute|hour|day|week|month)s?\s+ago", re.I)
_UNIT = {"minute": timedelta(minutes=1), "hour": timedelta(hours=1), "day": timedelta(days=1),
         "week": timedelta(weeks=1), "month": timedelta(days=30)}


def posted_at_to_iso(text: str | None, now: datetime | None = None) -> str | None:
    """Google's relative `posted_at` ("2 days ago", "30+ days ago", "Just posted") -> 'YYYY-MM-DD'."""
    text = clean(text)
    now = now or datetime.now(timezone.utc)
    match = _AGO.search(text)
    if match:
        return (now - int(match.group(1)) * _UNIT[match.group(2).lower()]).date().isoformat()
    if re.search(r"just posted|today", text, re.I):
        return now.date().isoformat()
    return to_iso(text)


def parse_serpapi(data: dict) -> list[Job]:
    jobs = []
    for j in data.get("jobs_results", []):
        options = j.get("apply_options") or []
        url = clean(options[0].get("link")) if options else ""
        jobs.append(Job(
            source="serpapi",
            title=clean(j.get("title")),
            company=clean(j.get("company_name")),
            url=url or clean(j.get("share_link")),
            location=clean(j.get("location")),
            description=clean(j.get("description")),
            is_remote="remote" in clean(j.get("location")).lower(),
            date_posted=posted_at_to_iso((j.get("detected_extensions") or {}).get("posted_at")),
        ))
    return [j for j in jobs if j.title and j.url]


def collect_serpapi(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    load_env()
    key = os.environ.get("SERPAPI_API_KEY")
    if not key:                                   # skipped, not an error
        return CollectorResult("serpapi", warning="SERPAPI_API_KEY is not set in .env; skipped")
    search = config["search"]
    own = (config.get("sources", {}).get("serpapi_google_jobs") or {}).get("queries")
    queries = own or search["queries"]
    jobs: list[Job] = []
    errors = []
    for query in queries[: (limit or len(queries))]:
        try:
            data = get_json(SERPAPI_URL, params={
                "engine": "google_jobs", "q": query, "location": search.get("location", "Israel"),
                "hl": "en", "api_key": key})
            jobs.extend(parse_serpapi(data))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{query}({type(e).__name__})")
    unique = list({j.id: j for j in jobs}.values())
    error = f"{len(errors)} queries failed: {', '.join(errors)}" if errors else None
    return CollectorResult("serpapi", unique[:limit] if limit else unique, error)
