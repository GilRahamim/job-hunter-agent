"""Collector registry: {name: fn} and collect_all()."""
from __future__ import annotations

import importlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from jobhunter.collectors.base import CollectorResult

log = logging.getLogger(__name__)

# registry name -> (module, function, config.yaml key under `sources`)
_SOURCES: dict[str, tuple[str, str, str]] = {
    "ats": ("ats", "collect_company_boards", "company_boards"),
    "jobspy": ("jobspy_source", "collect_jobspy", "jobspy"),
    "remotive": ("remote_boards", "collect_remotive", "remotive"),
    "remoteok": ("remote_boards", "collect_remoteok", "remoteok"),
    "himalayas": ("remote_boards", "collect_himalayas", "himalayas"),
    "arbeitnow": ("remote_boards", "collect_arbeitnow", "arbeitnow"),
    "weworkremotely": ("remote_boards", "collect_weworkremotely", "weworkremotely"),
    "serpapi": ("serpapi", "collect_serpapi", "serpapi_google_jobs"),
    "techmap": ("techmap", "collect_techmap", "techmap"),
    "getro": ("getro", "collect_getro", "getro"),
}

SOURCE_NAMES = list(_SOURCES)


def _load(name: str) -> Callable[..., CollectorResult]:
    module, func, _ = _SOURCES[name]
    return getattr(importlib.import_module(f"jobhunter.collectors.{module}"), func)


def _run_one(name: str, config: dict[str, Any], limit: int | None) -> tuple[CollectorResult, float]:
    start = time.monotonic()
    try:
        result = _load(name)(config, limit=limit)
    except Exception as e:  # noqa: BLE001 — collectors should not raise, but never trust that
        log.exception("collector %s crashed", name)
        result = CollectorResult(name, error=f"{type(e).__name__}: {e}")
    return result, time.monotonic() - start


def collect_all(config: dict[str, Any], only: list[str] | None = None,
                limit: int | None = None) -> tuple[list[CollectorResult], list[dict]]:
    """Run enabled sources in parallel (or just `only`). Returns (results, health records).

    `limit` caps jobs per source (per company for the ATS source)."""
    enabled_cfg = config.get("sources", {})
    if only:
        unknown = set(only) - set(_SOURCES)
        if unknown:
            raise ValueError(f"unknown source(s): {', '.join(sorted(unknown))}; known: {', '.join(SOURCE_NAMES)}")
        names = list(only)
    else:
        names = [n for n in _SOURCES
                 if (enabled_cfg.get(_SOURCES[n][2]) or {}).get("enabled", False)]

    with ThreadPoolExecutor(max_workers=max(1, len(names))) as pool:
        outcomes = list(pool.map(lambda n: _run_one(n, config, limit), names))

    results = [r for r, _ in outcomes]
    health = [{"source": r.source, "fetched": len(r.jobs), "error": r.error, "duration_s": round(d, 1)}
              for r, d in outcomes]
    return results, health
