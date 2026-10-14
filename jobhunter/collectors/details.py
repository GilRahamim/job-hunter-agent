"""Fill in missing job descriptions, so the experience rules can be checked.

LinkedIn results from the fixed pipeline and the Israeli Tech Map lists arrive without a description.
For LinkedIn job links the description is read with JobSpy's own job-page reader (not custom LinkedIn
scraping), one job at a time with a pause between calls."""
from __future__ import annotations

import logging
import random
import re
import time
from functools import lru_cache
from typing import Any

from jobhunter import stop
from jobhunter.collectors.base import clean
from jobhunter.models import Job

log = logging.getLogger(__name__)

_LINKEDIN_JOB = re.compile(r"linkedin\.com/jobs/view/(?:[^/?#]*-)?(\d{6,})")


def linkedin_job_id(url: str) -> str | None:
    m = _LINKEDIN_JOB.search(url or "")
    return m.group(1) if m else None


@lru_cache(maxsize=1)
def _linkedin_reader() -> Any:
    from jobspy.linkedin import LinkedIn
    from jobspy.model import DescriptionFormat, ScraperInput, Site

    reader = LinkedIn()
    reader.scraper_input = ScraperInput(site_type=[Site.LINKEDIN], description_format=DescriptionFormat.MARKDOWN)
    return reader


def fetch_description(job: Job) -> str:
    """The posting text for a LinkedIn job link, or "" when it cannot be read."""
    job_id = linkedin_job_id(job.url)
    if not job_id:
        return ""
    try:
        return clean(_linkedin_reader()._fetch_details(job_id).get("description"))
    except Exception as e:  # noqa: BLE001 - a missing description must never fail a run
        log.warning("description for %s failed: %s", job.url, e)
        return ""


def fill_descriptions(jobs: list[Job], limit: int, pause: tuple[float, float] = (1.0, 2.5)) -> int:
    """Fetch descriptions for up to `limit` jobs that have none, in place. Returns how many were filled."""
    todo = [j for j in jobs if not j.description.strip() and linkedin_job_id(j.url)][:limit]
    filled = 0
    for i, job in enumerate(todo):
        if stop.stop_requested():
            break
        if i:
            time.sleep(random.uniform(*pause))          # LinkedIn blocks fast sequential calls
        job.description = fetch_description(job)
        filled += bool(job.description)
    if todo:
        log.info("descriptions: filled %d of %d jobs that had none", filled, len(todo))
    return filled
