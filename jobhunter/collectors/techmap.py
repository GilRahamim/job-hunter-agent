"""Israeli Tech Map daily job lists (https://github.com/mluggy/techmap, ODbL v1.0).

One CSV per job category, refreshed daily, covering ~470 Israeli companies, including ones whose
own careers sites have no public API (most links are the company's LinkedIn posting). The CSVs have
no job descriptions: only title, company, level and city."""
from __future__ import annotations

import csv
import io
import logging
from typing import Any

from jobhunter.collectors.base import CollectorResult, clean, get_text, to_iso
from jobhunter.models import Job

log = logging.getLogger(__name__)

CSV_URL = "https://raw.githubusercontent.com/mluggy/techmap/main/jobs/{category}.csv"
DEFAULT_CATEGORIES = ["software", "data-science", "devops", "frontend", "hardware", "qa", "security", "support"]


def parse_techmap(text: str) -> list[Job]:
    jobs = []
    for row in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        city = clean(row.get("city"))
        level = clean(row.get("level"))
        jobs.append(Job(
            source="techmap",
            title=clean(row.get("title")),
            company=clean(row.get("company")),
            url=clean(row.get("url")),
            location=f"{city}, Israel" if city else "Israel",
            # no posting text in the dataset; the level ("Student", "Engineer", "Manager") helps the agent
            description=f"Level: {level}" if level else "",
            date_posted=to_iso(row.get("updated")),
        ))
    return [j for j in jobs if j.title and j.url]


def collect_techmap(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    categories = (config.get("sources", {}).get("techmap") or {}).get("categories") or DEFAULT_CATEGORIES
    jobs: list[Job] = []
    errors = []
    for category in categories:
        try:
            jobs.extend(parse_techmap(get_text(CSV_URL.format(category=category))))
        except Exception as e:  # noqa: BLE001 - keep the other categories
            errors.append(f"{category}({type(e).__name__})")
    unique = list({j.id: j for j in jobs}.values())
    error = f"{len(errors)}/{len(categories)} categories failed: {', '.join(errors)}" if errors else None
    if not unique and not error:
        error = "no jobs returned"
    return CollectorResult("techmap", unique[:limit] if limit else unique, error)
