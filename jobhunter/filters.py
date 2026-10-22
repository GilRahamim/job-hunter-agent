"""Stage 1: cheap rule filters (location, role, seniority, age) with per-reason drop counts."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date, timedelta
from typing import Any

from jobhunter.models import Job

# (?<![\d.]): "3.5 years" is not "5 years" and "2012 years" is not "12 years"
_YEARS = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d)?)(?:\s*(?:-|–|to)\s*\d{1,2}(?:\.\d)?)?\s*\+?\s*(?:or more\s+)?"
                    r"(?:years?\b|yrs?\b|yoe\b|שנות|שנים|שנה)"
                    # not a job requirement: "founded 10 years ago", "18 years old", "4+ years of driving"
                    r"(?!\s*(?:ago|old|(?:of\s+)?driving)\b)", re.I)
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
              "nine": 9, "ten": 10}
# "four years", "two (2) years", "three or more years" -> digits, so _YEARS can read them
_NUM_WORD = re.compile(r"\b(" + "|".join(_NUM_WORDS) + r")\b(?:\s*\(\d{1,2}\))?(?=\s*\+?\s*(?:or more\s+)?"
                       r"(?:years?|yrs?)\b)", re.I)
# "שלוש שנות ניסיון", "ארבע שנים" -> digits (longer forms first: "שלושה" before "שלוש")
_HE_NUM_WORDS = {"שתי": 2, "שלושה": 3, "שלוש": 3, "ארבעה": 4, "ארבע": 4, "חמישה": 5, "חמש": 5, "שישה": 6,
                 "שש": 6, "שבעה": 7, "שבע": 7, "שמונה": 8, "תשעה": 9, "תשע": 9, "עשר": 10}
_HE_NUM_WORD = re.compile(r"(?<![א-ת])(" + "|".join(_HE_NUM_WORDS) + r")(?=\s+(?:שנות|שנים))")
# the number after the words: "Years of experience: 4"
_YEARS_LABEL = re.compile(r"years of (?:relevant |professional |work |hands-on )?experience\s*[:\-–]\s*"
                          r"(\d{1,2}(?:\.\d)?)", re.I)
MAX_REQUIRED_YEARS = 15     # larger numbers describe the company ("over 20 years in the industry")
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


def excluded_title(title: str, f: dict[str, Any]) -> bool:
    """An `exclude_keywords` title ("Sales", "Technician") that no `exclude_exceptions` word rescues
    ("NOC Technician" is an entry-level operations job, "Field Technician" is not)."""
    return contains_any(title, f.get("exclude_keywords", [])) and \
        not contains_any(title, f.get("exclude_exceptions") or [])


def role_ok(title: str, cfg: dict[str, Any]) -> bool:
    f = cfg["filters"]
    return contains_any(title, f["role_keywords"]) and not excluded_title(title, f)


def role_fit(job: Job, cfg: dict[str, Any]) -> bool:
    """A computer-science role: a CS title, or a description asking for a CS / engineering
    degree or technical background ("Test Driver" at Mobileye asking for a B.Sc.).
    Excluded titles (sales, recruiter...) stay excluded either way."""
    f = cfg["filters"]
    if excluded_title(job.title, f):
        return False
    return contains_any(job.title, f["role_keywords"]) or \
        bool(keyword_hits(job.description, f.get("role_description_keywords") or []))


def seniority_ok(title: str, cfg: dict[str, Any]) -> bool:
    f = cfg["filters"]
    return not (f.get("exclude_senior") and word_match(title, f.get("senior_keywords", [])))


def required_years(text: str) -> float:
    """Largest 'N years' lower bound mentioned in the text (0 if none).
    Reads "3+ years", "1 year", "four years", "3+ YOE", "Years of experience: 4", "שנתיים",
    "שנת ניסיון" and "שלוש שנות ניסיון"."""
    text = _NUM_WORD.sub(lambda m: str(_NUM_WORDS[m.group(1).lower()]), text)
    text = _HE_NUM_WORD.sub(lambda m: str(_HE_NUM_WORDS[m.group(1)]), text)
    found = [y for rx in (_YEARS, _YEARS_LABEL) for m in rx.finditer(text)
             if (y := float(m.group(1))) <= MAX_REQUIRED_YEARS]
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


def years_limit(job: Job, cfg: dict[str, Any]) -> float | None:
    """The most years of experience this job may ask for (None = no limit); a junior title gets
    `junior_max_required_years`, like experience_ok."""
    f = cfg["filters"]
    max_years, junior_max = f.get("max_required_years"), f.get("junior_max_required_years")
    if max_years is None:
        return None
    if junior_max is not None and keyword_hits(job.title, f.get("junior_keywords") or []):
        return max(max_years, junior_max)
    return max_years


def years_over_limit(job: Job, years: float | None, cfg: dict[str, Any]) -> bool:
    """`years` (e.g. what the LLM read in the posting) is more than this job may ask for."""
    limit = years_limit(job, cfg)
    return limit is not None and years is not None and years > limit


def over_limit_score(score: float, years: float, limit: float) -> float:
    """Score of a stored job whose posting asks for `years` of experience, more than the `limit` this
    user allows (called only when years > limit). Keeps it below agent.min_match_score (70) and
    notify.min_score, so it never counts as a strong match or triggers a notification."""
    # Scale instead of a flat cap, so a better fit still ranks above a weaker one (100 -> 60 at most),
    # then 5 points less for every year over the first one past the limit.
    extra_years = max(0.0, years - limit - 1)
    return round(max(0.0, 0.6 * score - 5 * extra_years), 1)


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
    if not role_fit(job, cfg):
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
