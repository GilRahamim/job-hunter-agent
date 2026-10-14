"""Graceful stop: the dashboard writes data/stop.flag; a running search checks it between steps,
stops early and still saves what it found."""
from __future__ import annotations

import time
from pathlib import Path

from jobhunter.config import run_dir


def stop_path() -> Path:
    return run_dir() / "stop.flag"


def request_stop() -> None:
    path = stop_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stop", encoding="utf-8")


def clear_stop() -> None:
    stop_path().unlink(missing_ok=True)


def stop_requested() -> bool:
    return stop_path().exists()


def clear_stale_stop(max_age_s: float = 300) -> None:
    """At run start: drop a request left over from an earlier run, but keep a fresh one
    (the stop toggle can be switched on while the run is still starting)."""
    try:
        if time.time() - stop_path().stat().st_mtime > max_age_s:
            clear_stop()
    except OSError:
        pass
