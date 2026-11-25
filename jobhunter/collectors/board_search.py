"""Find company job boards with Google `site:` searches and read the jobs on the ones we do not follow.

A search like `(site:jobs.lever.co OR site:comeet.com/jobs) Junior Data Analyst israel` returns
postings on ATS sites (Comeet, Greenhouse, Lever, Ashby, SmartRecruiters). Every result link names
the company's board; the board is fetched with the ATS collectors' own code. Companies already in
companies.yaml are skipped (the daily run reads them anyway), so this reaches the other ones.

One SerpAPI search per query (the same monthly quota as the Google Jobs source), so it is not part of
the daily run: the search agent uses it as the `board_search` source, and
`scripts/discover_boards.py` uses `boards_in` / `group_dorks` to add boards to companies.yaml."""
from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from jobhunter.collectors import ats
from jobhunter.collectors.base import CollectorResult, get_json
from jobhunter.collectors.serpapi import SERPAPI_URL
from jobhunter.config import load_companies, load_env
from jobhunter.models import Job

log = logging.getLogger(__name__)

BOARD_PATTERNS = {                    # careers links / pages -> (ats, entry)
    "comeet": re.compile(r"comeet\.com/jobs/([\w-]+)/([0-9A-Fa-f]{2}\.[0-9A-Fa-f]{3})"),
    "greenhouse": re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"),
    "lever": re.compile(r"jobs\.(?:eu\.)?lever\.co/([\w-]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)"),            # "monday.com" is a real slug
    "smartrecruiters": re.compile(r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)"),
}
_SKIP_SLUGS = {"embed", "js", "jobs", "api", "v1"}
DEFAULT_DOMAINS = ["comeet.com/jobs", "boards.greenhouse.io", "job-boards.greenhouse.io",
                   "jobs.lever.co", "jobs.ashbyhq.com", "jobs.smartrecruiters.com"]


def boards_in(text: str) -> set[tuple[str, str]]:
    """(ats, entry) for every board a text or link names: "comeet", "<slug>/<uid>"; the others, the slug."""
    found = set()
    for kind, rx in BOARD_PATTERNS.items():
        for m in rx.finditer(text):
            if kind == "comeet":
                found.add((kind, f"{m.group(1).lower()}/{m.group(2).upper()}"))
            elif m.group(1).lower() not in _SKIP_SLUGS:
                found.add((kind, m.group(1).lower() if kind != "smartrecruiters" else m.group(1)))
    return found


def settings(config: dict[str, Any]) -> dict[str, Any]:
    return (config.get("sources", {}).get("board_search") or {})


def dork(query: str, config: dict[str, Any]) -> str:
    """`(site:a OR site:b) <query> israel`: one Google search over every ATS domain."""
    s = settings(config)
    sites = " OR ".join(f"site:{d}" for d in s.get("domains") or DEFAULT_DOMAINS)
    return f"({sites}) {query} {s.get('location_word', 'israel')}".strip()


def group_dorks(config: dict[str, Any]) -> list[str]:
    """One search per role group of the agent: `junior ("AI Engineer" OR "LLM Engineer" ...)`, so a
    run covers every kind of job. Titles per group are capped by sources.board_search.titles_per_group."""
    cap = settings(config).get("titles_per_group", 4)
    groups = config.get("agent", {}).get("role_groups") or {}
    return [dork("junior (" + " OR ".join(f'"{t}"' for t in titles[:cap]) + ")", config)
            for titles in groups.values() if titles]


def followed(config: dict[str, Any]) -> set[tuple[str, str]]:
    """Boards already in companies.yaml, lowercased."""
    try:
        companies = load_companies()
    except Exception:  # noqa: BLE001 - a missing file only means nothing is followed
        return set()
    return {(kind, str(e).lower()) for kind, entries in companies.items()
            for e in entries or [] if not isinstance(e, dict)}


def search_boards(query: str, config: dict[str, Any], key: str) -> set[tuple[str, str]]:
    """Boards named in the results of one dork search (one SerpAPI call)."""
    data = get_json(SERPAPI_URL, params={
        "engine": "google", "q": dork(query, config), "num": settings(config).get("results", 50),
        "hl": "en", "api_key": key})
    links = " ".join(r.get("link", "") for r in data.get("organic_results", []))
    return boards_in(links)


def collect_board_search(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    """Jobs on the boards the dork searches name, for each query in `search.queries`."""
    load_env()
    key = os.environ.get("SERPAPI_API_KEY")
    if not key:                                   # skipped, not an error
        return CollectorResult("board_search", warning="SERPAPI_API_KEY is not set in .env; skipped")
    boards: set[tuple[str, str]] = set()
    errors: list[str] = []
    for query in config["search"]["queries"][: limit or None]:
        try:
            boards |= search_boards(query, config, key)
        except Exception as e:  # noqa: BLE001 - one failed search must not stop the run
            errors.append(f"{query}({type(e).__name__})")
    skip = followed(config)
    todo = sorted(b for b in boards if (b[0], b[1].lower()) not in skip)
    todo = todo[: settings(config).get("max_boards", 15)]
    jobs: list[Job] = []

    def read(board: tuple[str, str]) -> list[Job]:
        try:
            return ats.FETCHERS[board[0]](board[1])
        except Exception as e:  # noqa: BLE001 - a dead board is common
            errors.append(f"{board[1]}({type(e).__name__})")
            return []

    with ThreadPoolExecutor(max_workers=8) as pool:
        for found in pool.map(read, todo):
            jobs.extend(found)
    log.info("board_search: %d boards named, %d new, %d jobs", len(boards), len(todo), len(jobs))
    error = f"{len(errors)} failed: {', '.join(errors[:5])}" if errors else None
    return CollectorResult("board_search", jobs, error)
