"""Google Jobs through SerpAPI (optional; skipped without SERPAPI_API_KEY)."""
from __future__ import annotations

import logging
import os
from typing import Any

from jobhunter.collectors.base import CollectorResult, clean, get_json, to_iso
from jobhunter.config import load_env
from jobhunter.models import Job

log = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"


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
            date_posted=to_iso((j.get("detected_extensions") or {}).get("posted_at")),
        ))
    return [j for j in jobs if j.title and j.url]


def collect_serpapi(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    load_env()
    key = os.environ.get("SERPAPI_API_KEY")
    if not key:
        return CollectorResult("serpapi")        # skipped, not an error
    search = config["search"]
    jobs: list[Job] = []
    errors = []
    for query in search["queries"][: (limit or len(search["queries"]))]:
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
