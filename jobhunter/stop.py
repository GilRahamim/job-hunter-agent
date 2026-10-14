"""Graceful stop: the dashboard writes <run dir>/stop.flag; a running search checks it between steps,
stops early and still saves what it found. `user=None` means the user of this process."""
from __future__ import annotations

import time
from pathlib import Path

from jobhunter.config import run_dir


def stop_path(user: str | None = None) -> Path:
    return run_dir(user) / "stop.flag"


def request_stop(user: str | None = None) -> None:
    path = stop_path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stop", encoding="utf-8")


def clear_stop(user: str | None = None) -> None:
    stop_path(user).unlink(missing_ok=True)


def stop_requested(user: str | None = None) -> bool:
    return stop_path(user).exists()


def clear_stale_stop(max_age_s: float = 300, user: str | None = None) -> None:
    """At run start: drop a request left over from an earlier run, but keep a fresh one
    (the stop toggle can be switched on while the run is still starting)."""
    try:
        if time.time() - stop_path(user).stat().st_mtime > max_age_s:
            clear_stop(user)
    except OSError:
        pass
