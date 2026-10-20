"""One run at a time: <run dir>/run.lock holds the PID of the running search (pipeline or agent loop).
The CLI and the dashboard button both take this lock."""
from __future__ import annotations

import os
from pathlib import Path

from jobhunter import stop
from jobhunter.config import run_dir


def lock_path(user: str | None = None) -> Path:
    return run_dir(user) / "run.lock"


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)      # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return code.value == 259                                # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def running_pid(user: str | None = None) -> int | None:
    """PID of the run holding the lock, or None when no live run holds it."""
    try:
        pid = int(lock_path(user).read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) else None


class RunLocked(RuntimeError):
    pass


class run_lock:
    """Context manager around run.lock. Clears a stale stop request on entry and the stop flag on exit."""

    def __init__(self, path: Path | None = None):
        self.path = path or lock_path()

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                pid = int(self.path.read_text().strip())
            except ValueError:
                pid = 0
            if pid_alive(pid) and pid != os.getpid():
                raise RunLocked(f"another run is in progress (pid {pid}); remove {self.path} if stale")
        self.path.write_text(str(os.getpid()))
        stop.clear_stale_stop()               # a stop request left from an earlier run must not end this one
        return self

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)
        stop.clear_stop()
