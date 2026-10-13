"""Stage 1: cheap rule filters (location, role, seniority, age) with per-reason drop counts."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from typing import Any

from jobhunter.models import Job

ISRAEL_EN = (
    r"\bisrael\b|tel[\s-]?aviv|\btlv\b|jaffa|herzli?ya|haifa|jerusalem|petah?[\s-]?tikva|petach|"
    r"ramat[\s-]?gan|givatayim|bnei[\s-]?brak|ra'?anana|netanya|rehovot|ness?[\s-]?ziona|"
    r"rishon[\s-]?le[\s-]?zion|holon|bat[\s-]?yam|or[\s-]?yehuda|airport[\s-]?city|yokneam|"
    r"kiryat[\s-]?gat|be'?er[\s-]?sheva|beersheba|caesarea|hod[\s-]?hasharon|kfar[\s-]?saba|"
    r"modi'?in|rosh[\s-]?ha'?ayin|nazareth|ashdod|ashkelon|\blod\b|ramla"
)
ISRAEL_HE = (
    r"ישראל|תל[\s-]?אביב|יפו|הרצליה|חיפה|ירושלים|פתח[\s-]?תקו?וה|רמת[\s-]?גן|גבעתיים|בני[\s-]?ברק|"
    r"רעננה|נתניה|רחובות|נס[\s-]?ציונה|ראשון[\s-]?לציון|חולון|בת[\s-]?ים|אור[\s-]?יהודה|יקנעם|"
    r"קרי?ית[\s-]?גת|באר[\s-]?שבע|קיסריה|הוד[\s-]?השרון|כפר[\s-]?סבא|מודיעין|ראש[\s-]?העין|"
    r"אשדוד|אשקלון|לוד|רמלה|נצרת"
)
IL_CODE = r"(?:^|[,(\s])IL(?:$|[,)\s])"          # case-SENSITIVE: "Petah Tikva, IL"
REMOTE_WORD = r"\bremote\b|work from home|\bwfh\b|anywhere|worldwide|מהבית|מרחוק"
EXCLUDE_REGION = (
    r"\b(us|usa|u\.s\.a?|united states|canada|latam|latin america|uk|united kingdom|apac|"
    r"australia|india|brazil|mexico|philippines|north america|americas)\b|\b(est|pst|cst|mst|et|pt)\b"
)

_isr = re.compile(ISRAEL_EN + "|" + ISRAEL_HE, re.I)
_il = re.compile(IL_CODE)
_remote = re.compile(REMOTE_WORD, re.I)
_ex = re.compile(EXCLUDE_REGION, re.I)


def is_israel(text: str) -> bool:
    return bool(_isr.search(text) or _il.search(text))


def region_pattern(regions_ok: list[str]) -> re.Pattern[str]:
    return re.compile("|".join(re.escape(r) for r in regions_ok) or r"(?!x)x", re.I)


def remote_ok(location: str, region: str = "", is_remote: bool = False,
              ok: re.Pattern[str] | None = None) -> bool:
    ok = ok or region_pattern(["worldwide", "anywhere", "global", "emea", "europe", "israel",
                               "middle east", "international"])
    text = f"{location} {region}"
    if not (is_remote or _remote.search(text)):
        return False
    if is_israel(text) or ok.search(text):     # an explicit OK wins: "US or EMEA" is fine
        return True
    if _ex.search(text):
        return False
    # bare "Remote" with no other location words and no region -> assume open
    return region.strip() == "" and not re.search(r"\w", _remote.sub("", location))


def location_ok(location: str, region: str = "", is_remote: bool = False,
                ok: re.Pattern[str] | None = None) -> bool:
    return is_israel(location) or remote_ok(location, region, is_remote, ok)


# ------------------------------------------------------------ title rules

def _norm_title(title: str) -> tuple[str, str]:
    """(padded lower-case title, same with punctuation turned into spaces)."""
    raw = f" {title.lower()} "
    return raw, " " + re.sub(r"[^\w֐-׿]+", " ", title.lower()) + " "


def contains_any(title: str, keywords: list[str]) -> bool:
    """Substring match on the padded title, so keywords like ' ai ' and 'ml ' work."""
    raw, spaced = _norm_title(title)
    return any(k.lower() in raw or k.lower() in spaced for k in keywords)


def word_match(title: str, keywords: list[str]) -> bool:
    """Whole-word match (so 'lead' does not hit 'leading', 'sr ' does not hit 'usr ')."""
    t = title.lower()
    for k in keywords:
        k = k.lower().strip()
        if k and re.search(rf"(?<!\w){re.escape(k)}(?!\w)", t):
            return True
    return False


def role_ok(title: str, cfg: dict[str, Any]) -> bool:
    f = cfg["filters"]
    return contains_any(title, f["role_keywords"]) and not contains_any(title, f.get("exclude_keywords", []))


def seniority_ok(title: str, cfg: dict[str, Any]) -> bool:
    f = cfg["filters"]
    return not (f.get("exclude_senior") and word_match(title, f.get("senior_keywords", [])))


def age_ok(date_posted: str | None, max_age_days: int | None, today: date | None = None) -> bool:
    if not date_posted or not max_age_days:
        return True                     # unknown dates are kept
    try:
        posted = date.fromisoformat(date_posted[:10])
    except ValueError:
        return True
    return posted >= (today or date.today()) - timedelta(days=max_age_days)


# ------------------------------------------------------------ pipeline stage

def drop_reason(job: Job, cfg: dict[str, Any], ok: re.Pattern[str], today: date | None = None) -> str | None:
    f = cfg["filters"]
    israel = f.get("israel", True) and is_israel(job.location)
    remote = f.get("remote", True) and remote_ok(job.location, job.remote_region, job.is_remote, ok)
    if not (israel or remote):
        return "location"
    if not role_ok(job.title, cfg):
        return "role"
    if not seniority_ok(job.title, cfg):
        return "senior"
    if not age_ok(job.date_posted, f.get("max_age_days"), today):
        return "age"
    return None


def filter_jobs(jobs: list[Job], cfg: dict[str, Any], today: date | None = None) -> tuple[list[Job], Counter]:
    """Returns (kept jobs, drop counts by reason)."""
    ok = region_pattern(cfg["filters"].get("remote_regions_ok", []))
    kept: list[Job] = []
    dropped: Counter = Counter()
    for job in jobs:
        reason = drop_reason(job, cfg, ok, today)
        if reason:
            dropped[reason] += 1
        else:
            kept.append(job)
    return kept, dropped
