"""Venture-capital portfolio job boards on Getro (e.g. Israel VC Forum: ~880 portfolio companies of
Israeli funds). The board's own search API, filtered to Israel; boards are listed in config.yaml.

Results carry no description, only a Getro seniority ("entry_level", "mid_senior"...), which is put
in the description so the experience rules can see it. Each job links to the company's real ATS page;
scripts/sync_companies.py adds those boards to companies.yaml, where full descriptions come from."""
from __future__ import annotations

import logging
import time
from typing import Any

from jobhunter.collectors.base import TIMEOUT, CollectorResult, clean, get_session, to_iso
from jobhunter.models import Job

log = logging.getLogger(__name__)

SEARCH_URL = "https://api.getro.com/api/v2/collections/{id}/search/jobs"
PAGE_SIZE = 20                     # the API rejects larger pages
MAX_PAGES = 100
PAUSE_S = 0.5                      # the boards' robots.txt asks for a 1 s crawl delay on pages


def search_page(board_id: int | str, page: int, location: str = "Israel") -> dict:
    resp = get_session().post(SEARCH_URL.format(id=board_id), timeout=TIMEOUT,
                              headers={"Accept": "application/json"},     # 406 without it
                              json={"hits_per_page": PAGE_SIZE, "page": page, "query": "",
                                    "filters": {"searchable_locations": [location]}})
    resp.raise_for_status()
    return resp.json().get("results") or {}


def parse_getro(results: dict) -> list[Job]:
    jobs = []
    for j in results.get("jobs") or []:
        org = j.get("organization") or {}
        locations = [clean(x) for x in j.get("locations") or []]
        seniority = clean(j.get("seniority"))
        jobs.append(Job(
            source="getro",
            title=clean(j.get("title")),
            company=clean(org.get("name")),
            url=clean(j.get("url")),
            location=" / ".join(x for x in locations if x),
            description=f"Seniority: {seniority.replace('_', ' ')}" if seniority else "",
            is_remote=clean(j.get("work_mode")).lower() == "remote",
            date_posted=to_iso(j.get("created_at")),
        ))
    return [j for j in jobs if j.title and j.url]


def fetch_board(board_id: int | str) -> list[Job]:
    jobs: list[Job] = []
    for page in range(MAX_PAGES):
        results = search_page(board_id, page)
        batch = parse_getro(results)
        jobs.extend(batch)
        if not batch or len(jobs) >= (results.get("count") or 0):
            break
        time.sleep(PAUSE_S)
    return jobs


def collect_getro(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    boards = (config.get("sources", {}).get("getro") or {}).get("boards") or []
    jobs: list[Job] = []
    errors = []
    for board in boards:
        try:
            jobs.extend(fetch_board(board["id"]))
        except Exception as e:  # noqa: BLE001 - keep the other boards
            errors.append(f"{board.get('name', board['id'])}({type(e).__name__})")
    unique = list({j.id: j for j in jobs}.values())
    error = f"{len(errors)}/{len(boards)} boards failed: {', '.join(errors)}" if errors else None
    return CollectorResult("getro", unique[:limit] if limit else unique, error)
