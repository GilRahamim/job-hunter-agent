"""Fill in missing job descriptions, so the experience rules can be checked.

LinkedIn results from the fixed pipeline and the Israeli Tech Map lists arrive without a description.
For LinkedIn job links the description is read with JobSpy's own job-page reader (not custom LinkedIn
scraping), one job at a time with a pause between calls. The same page also tells whether LinkedIn
still accepts applications ("No longer accepting applications"), so closed jobs can be dropped."""
from __future__ import annotations

import logging
import random
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

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
    if not hasattr(reader, "session"):        # python-jobspy 1.4+ builds it in scrape(), the same way
        from jobspy.linkedin.constant import headers
        from jobspy.util import RequestsRotating, create_session

        reader.session = create_session(RequestsRotating(reader.scraper_input.proxies, clear_cookies=True),
                                        reader.scraper_input, headers)
    return reader


@dataclass
class Posting:
    description: str = ""
    closed: bool = False          # LinkedIn shows "No longer accepting applications"
    rate_limited: bool = False    # LinkedIn answered 429: stop asking it this run


def parse_posting(html: str) -> Posting:
    """Description and closed flag from a LinkedIn job page, parsed with JobSpy's own helpers."""
    from bs4 import BeautifulSoup
    from jobspy.model import DescriptionFormat

    soup = BeautifulSoup(html or "", "html.parser")
    div = soup.find("div", class_="show-more-less-html__markup")
    if div:
        div.attrs.clear()
    markup = div.prettify(formatter="html") if div else None
    closed = soup.find(class_="closed-job__flavor--closed") is not None
    return Posting(clean(_to_markdown(markup, DescriptionFormat.MARKDOWN)), closed)


def _to_markdown(markup: str | None, fmt: Any) -> str | None:
    """JobSpy's own HTML -> markdown step; it moved in python-jobspy 1.4."""
    try:
        from jobspy.util import description_fields          # 1.4+
    except ImportError:
        from jobspy.linkedin import format_description      # up to 1.3
        return format_description(markup, fmt)[0]
    return description_fields(markup, fmt)["description"]


def fetch_posting(job: Job) -> Posting:
    """The LinkedIn page of a job: its text and whether it is closed. Empty when it cannot be read."""
    job_id = linkedin_job_id(job.url)
    if not job_id:
        return Posting()
    try:
        reader = _linkedin_reader()
        resp = reader.session.get(f"{reader.base_url}/jobs/view/{job_id}", timeout=15)
        if resp.status_code != 200 or not urlparse(resp.url).path.startswith("/jobs/view/"):
            log.warning("posting %s: status %s, url %s", job.url, resp.status_code, resp.url)
            return Posting(rate_limited=resp.status_code == 429)
        return parse_posting(resp.text)
    except Exception as e:  # noqa: BLE001 - a missing description must never fail a run
        log.warning("posting %s failed: %s", job.url, e)
        return Posting()


def fill_descriptions(jobs: list[Job], limit: int, pause: tuple[float, float] = (1.0, 2.5)) -> set[str]:
    """Fetch descriptions for up to `limit` jobs that have none, in place.
    Returns the ids of jobs LinkedIn marks as no longer accepting applications."""
    todo = [j for j in jobs if not j.description.strip() and linkedin_job_id(j.url)][:limit]
    filled, closed = 0, set()
    for i, job in enumerate(todo):
        if stop.stop_requested():
            break
        if i:
            time.sleep(random.uniform(*pause))          # LinkedIn blocks fast sequential calls
        posting = fetch_posting(job)
        if posting.rate_limited:
            log.warning("descriptions: LinkedIn rate-limited (429), skipping the remaining %d jobs",
                        len(todo) - i)
            break
        job.description = posting.description
        filled += bool(job.description)
        if posting.closed:
            closed.add(job.id)
    if todo:
        log.info("descriptions: filled %d of %d jobs that had none, %d closed", filled, len(todo), len(closed))
    return closed
