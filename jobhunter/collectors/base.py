"""Shared HTTP session, text/date helpers and the collector result type."""
from __future__ import annotations

import html as html_lib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from jobhunter.models import Job

log = logging.getLogger(__name__)

TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (JobHunterAgent)"


@dataclass
class CollectorResult:
    source: str
    jobs: list[Job] = field(default_factory=list)
    error: str | None = None      # shown on the dashboard "Sources" tab
    warning: str | None = None    # partial miss that still returned jobs; not counted as a failure


@lru_cache(maxsize=1)
def get_session() -> requests.Session:
    """One session: User-Agent, retry 3x with backoff on 429/5xx."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET", "POST"), respect_retry_after_header=True)
    adapter = HTTPAdapter(max_retries=retry, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(url: str, **kwargs: Any) -> Any:
    resp = get_session().get(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.json()


def get_text(url: str, **kwargs: Any) -> str:
    resp = get_session().get(url, timeout=TIMEOUT, **kwargs)
    resp.raise_for_status()
    return resp.text


def html_to_text(html: str | None) -> str:
    """HTML (or HTML-escaped HTML, as Greenhouse sends) -> plain text."""
    text = html_lib.unescape(html or "")
    text = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def to_iso(value: Any) -> str | None:
    """ISO strings, unix seconds and unix milliseconds -> 'YYYY-MM-DD' (or None)."""
    if value in (None, "", 0):
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
            n = float(value)
            if n > 1e11:          # milliseconds
                n /= 1000
            return datetime.fromtimestamp(n, tz=timezone.utc).date().isoformat()
        text = str(value).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]):
            return text[:10]
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(text).date().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def clean(value: Any) -> str:
    """Coerce None / NaN / non-strings to a stripped string."""
    if value is None or (isinstance(value, float) and value != value):
        return ""
    return str(value).strip()
