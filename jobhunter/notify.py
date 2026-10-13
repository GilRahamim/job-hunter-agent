"""Optional desktop notification after a run when new strong matches were found (config: notify)."""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Callable

log = logging.getLogger(__name__)

_PS_TOAST = """
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(8000, $env:JH_TITLE, $env:JH_TEXT, [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 9
$n.Dispose()
"""


def windows_balloon(title: str, text: str) -> None:
    """Fire-and-forget balloon notification (no extra modules needed)."""
    import os
    env = {**os.environ, "JH_TITLE": title, "JH_TEXT": text}
    subprocess.Popen(["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", _PS_TOAST],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def strong_matches(rows: list[dict], min_score: float) -> list[dict]:
    return sorted((r for r in rows if (r.get("score") or 0) >= min_score),
                  key=lambda r: r["score"], reverse=True)


def notify_strong_matches(rows: list[dict], cfg: dict[str, Any],
                          sender: Callable[[str, str], None] = windows_balloon) -> int:
    """Returns how many strong matches were announced (0 when disabled or none)."""
    n_cfg = cfg.get("notify") or {}
    if not n_cfg.get("enabled"):
        return 0
    found = strong_matches(rows, n_cfg.get("min_score", 80))
    if not found:
        return 0
    top = found[0]
    text = f"{top['title']} @ {top['company']} ({top['score']:.0f})"
    if len(found) > 1:
        text += f" +{len(found) - 1}"
    try:
        sender(f"Job Hunter: {len(found)} new strong matches", text)
    except Exception as e:  # noqa: BLE001 - a notification must never fail a run
        log.warning("notification failed: %s", e)
        return 0
    return len(found)
