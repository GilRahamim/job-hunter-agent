"""LinkedIn / Indeed / Glassdoor / Google Jobs through the python-jobspy library."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

from jobhunter import stop
from jobhunter.collectors.base import CollectorResult, clean, to_iso
from jobhunter.models import Job

log = logging.getLogger(__name__)

# Remote pass only for queries that look like AI / ML roles.
_REMOTE_QUERY_HINTS = ("ai", "llm", "genai", "machine learning", "ml ", "data scientist")


def frame_to_jobs(df: Any) -> list[Job]:
    """Convert a JobSpy DataFrame (or a CSV loaded with pandas) to Jobs."""
    import pandas as pd

    jobs = []
    for row in df.to_dict("records"):
        url = clean(row.get("job_url_direct")) or clean(row.get("job_url"))
        site = clean(row.get("site")) or "unknown"
        is_remote = row.get("is_remote")
        job = Job(
            source=f"jobspy:{site}",
            title=clean(row.get("title")),
            company=clean(row.get("company")),
            url=url,
            location=clean(row.get("location")),
            description=clean(row.get("description")),
            is_remote=bool(is_remote) if pd.notna(is_remote) else False,
            date_posted=to_iso(clean(row.get("date_posted"))),
        )
        if job.title and job.url:
            jobs.append(job)
    return jobs


def _scrape(sites: list[str], query: str, cfg: dict[str, Any], location: str,
            remote: bool, fetch_desc: bool) -> list[Job]:
    from jobspy import scrape_jobs

    search = cfg["search"]
    kwargs: dict[str, Any] = dict(
        search_term=query,
        google_search_term=f"{query} jobs in {location} since last week",
        location=location,
        country_indeed="israel",
        results_wanted=search["results_per_query"],
        hours_old=search["hours_old"],
        linkedin_fetch_description=fetch_desc,
    )
    if remote:
        kwargs["is_remote"] = True
    try:
        return frame_to_jobs(scrape_jobs(site_name=sites, **kwargs))
    except Exception as e:  # noqa: BLE001 — retry per site so one failure keeps the rest
        log.warning("jobspy combined call failed for %r (%s); retrying per site", query, e)
    jobs: list[Job] = []
    for site in sites:
        try:
            # Indeed cannot combine hours_old with is_remote
            kw = {k: v for k, v in kwargs.items() if not (site == "indeed" and k == "is_remote")}
            jobs.extend(frame_to_jobs(scrape_jobs(site_name=[site], **kw)))
        except Exception as e:  # noqa: BLE001
            log.warning("jobspy %s failed for %r: %s", site, query, e)
    return jobs


def collect_jobspy(config: dict[str, Any], limit: int | None = None) -> CollectorResult:
    try:
        import jobspy  # noqa: F401
    except ImportError:
        return CollectorResult("jobspy", error="python-jobspy is not installed")

    src = config["sources"]["jobspy"]
    sites = src.get("sites", ["linkedin", "indeed", "glassdoor", "google"])
    queries = config["search"]["queries"]
    if limit:
        queries = queries[:max(1, limit // 10)] if limit < 20 else queries
    base_loc = config["search"].get("location", "Israel")
    fetch_desc = bool(src.get("fetch_linkedin_descriptions", False))

    jobs: list[Job] = []
    failed = 0
    passes = [(q, base_loc, False) for q in queries] + [
        (q, "Remote", True) for q in queries if any(h in q.lower() + " " for h in _REMOTE_QUERY_HINTS)]
    for query, location, remote in passes:
        if stop.stop_requested():
            log.info("jobspy: stop requested, skipping the remaining queries")
            break
        try:
            found = _scrape(sites, query, config, location, remote, fetch_desc)
            jobs.extend(found)
            if not found:
                failed += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            log.warning("jobspy query %r failed: %s", query, e)
        time.sleep(random.uniform(2, 4))   # parallel / fast queries get LinkedIn to block us
        if limit and len(jobs) >= limit:
            break

    unique = list({j.id: j for j in jobs}.values())
    if not unique:
        return CollectorResult("jobspy", error="no jobs returned (rate-limited or blocked?)")
    # Some queries simply have no matches; that is normal as long as others found jobs.
    warning = f"{failed}/{len(passes)} query passes returned nothing" if failed else None
    return CollectorResult("jobspy", unique[:limit] if limit else unique, warning=warning)
