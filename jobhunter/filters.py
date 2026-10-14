"""Stage 1: cheap rule filters (location, role, seniority, age) with per-reason drop counts."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from typing import Any

from jobhunter.models import Job

_YEARS = re.compile(r"(\d{1,2})(?:\s*(?:-|–|to)\s*\d{1,2})?\s*\+?\s*(?:or more\s+)?"
                    r"(?:years?\b|yrs?\b|שנות|שנים|שנה)"
                    r"(?!\s*(?:ago|old)\b)", re.I)       # "founded 10 years ago" is not a requirement
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
              "nine": 9, "ten": 10}
# "four years", "two (2) years", "three or more years" -> digits, so _YEARS can read them
_NUM_WORD = re.compile(r"\b(" + "|".join(_NUM_WORDS) + r")\b(?:\s*\(\d{1,2}\))?(?=\s*\+?\s*(?:or more\s+)?"
                       r"(?:years?|yrs?)\b)", re.I)
_HE_YEARS = ((re.compile(r"שנתיים"), 2), (re.compile(r"שנת\s+ניסיון"), 1))
_HEBREW = re.compile(r"[֐-׿]")

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


def required_years(text: str) -> float:
    """Largest 'N years' lower bound mentioned in the text (0 if none).
    Reads "3+ years", "1 year", "four years", "שנתיים" and "שנת ניסיון"."""
    text = _NUM_WORD.sub(lambda m: str(_NUM_WORDS[m.group(1).lower()]), text)
    found = [int(m.group(1)) for m in _YEARS.finditer(text)]
    found += [n for rx, n in _HE_YEARS if rx.search(text)]
    return float(max(found)) if found else 0.0


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    """Keywords found in the text: whole words for English, substrings for Hebrew
    (Hebrew glues one-letter prefixes on: "לסטודנטים")."""
    low = text.lower()
    hits = []
    for k in keywords:
        k = k.lower().strip()
        if k and (k in low if _HEBREW.search(k) else re.search(rf"(?<!\w){re.escape(k)}(?!\w)", low)):
            hits.append(k)
    return hits


def junior_signals(job: Job, keywords: list[str]) -> list[str]:
    """Junior / entry-level words in the title or description ("junior", "graduate", "ללא ניסיון")."""
    return keyword_hits(f"{job.title}\n{job.description}", keywords)


def experience_ok(job: Job, max_years: float | None, junior_max_years: float | None = None,
                  junior_keywords: list[str] | None = None,
                  experienced_phrases: list[str] | None = None) -> bool:
    """Junior mode: keep jobs that state no more than `max_years` of required experience.
    A junior title ("Junior Data Engineer, 1-2 years") may state up to `junior_max_years`.
    Phrases like "extensive experience" drop a job unless its title says junior."""
    if max_years is None:
        return True
    junior_title = bool(keyword_hits(job.title, junior_keywords or []))
    limit = max(max_years, junior_max_years) if junior_title and junior_max_years is not None else max_years
    if required_years(f"{job.title}\n{job.description}") > limit:
        return False
    return junior_title or not keyword_hits(job.description, experienced_phrases or [])


def junior_reason(job: Job, cfg: dict[str, Any]) -> str | None:
    """Why a job is not a junior job ("senior" / "experience" / "unverified"), or None when it is.
    Shared by the filter stage, the rescore step, the agent's save guard and the dashboard."""
    f = cfg["filters"]
    if not seniority_ok(job.title, cfg):
        return "senior"
    words = f.get("junior_keywords") or []
    if not experience_ok(job, f.get("max_required_years"), f.get("junior_max_required_years"),
                         words, f.get("experienced_phrases")):
        return "experience"
    # No description: the years requirement cannot be checked, so keep it only if the title says junior.
    if f.get("drop_unverified") and not job.description.strip() and not keyword_hits(job.title, words):
        return "unverified"
    return None


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
    reason = junior_reason(job, cfg)
    if reason:
        return reason
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
