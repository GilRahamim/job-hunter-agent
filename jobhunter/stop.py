"""Graceful stop: the dashboard writes data/stop.flag; a running search checks it between steps,
stops early and still saves what it found."""
from __future__ import annotations

import time

from jobhunter.config import ROOT

STOP_PATH = ROOT / "data" / "stop.flag"


def request_stop() -> None:
    STOP_PATH.parent.mkdir(parents=True, exist_ok=True)
    STOP_PATH.write_text("stop", encoding="utf-8")


def clear_stop() -> None:
    STOP_PATH.unlink(missing_ok=True)


def stop_requested() -> bool:
    return STOP_PATH.exists()


def clear_stale_stop(max_age_s: float = 300) -> None:
    """At run start: drop a request left over from an earlier run, but keep a fresh one
    (the stop toggle can be switched on while the run is still starting)."""
    try:
        if time.time() - STOP_PATH.stat().st_mtime > max_age_s:
            clear_stop()
    except OSError:
        pass
