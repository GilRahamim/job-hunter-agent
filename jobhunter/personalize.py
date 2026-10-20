"""`auto_from_cv: true` (set for users created from the dashboard): search settings come from the CV.

config.yaml is hand-tuned for the owner (junior roles in computer science). Someone who only uploads
a CV — maybe in marketing, maybe with 6 years of experience — needs other search terms, another role
filter and another experience limit. This derives them from their CandidateProfile:

  search.queries         the user's own titles (their config.yaml), else the CV's target roles
  filters.role_keywords  the meaningful words of those titles
  exclude / senior words the owner's lists minus anything that appears in those titles
  experience limit       up to (CV years + 2), no limit for senior candidates
  employer searches,     cleared: the owner's banks / health funds searches and "open to NOC / SOC"
  preferences            text are written for the owner's field
"""
from __future__ import annotations

import copy
import logging
import math
import re
from typing import Any

from jobhunter.filters import contains_any
from jobhunter.models import CandidateProfile

log = logging.getLogger(__name__)

# Words that say nothing about the field of a title.
_GENERIC = {"junior", "jr", "senior", "sr", "entry", "level", "lead", "head", "intern", "internship",
            "student", "graduate", "trainee", "remote", "hybrid", "of", "and", "the", "for", "to", "in",
            "with", "at", "an", "or", "i", "ii", "iii"}
_TITLE_WORD = re.compile(r"[\w+#]+")
SHORT_WORD = 3          # words this short ("qa", "ux", "hr") must match as whole words
YEARS_MARGIN = 2        # jobs may ask for up to this many years more than the CV shows


def role_words(titles: list[str]) -> list[str]:
    """Role keywords from job titles, in the form filters.contains_any expects
    ("Digital Marketing Specialist", "UX Writer" -> "digital", "marketing", "specialist", " ux ", "writer")."""
    words: list[str] = []
    for title in titles:
        for w in _TITLE_WORD.findall(title.lower()):
            if w in _GENERIC:
                continue
            kw = f" {w} " if len(w) <= SHORT_WORD else w
            if kw not in words:
                words.append(kw)
    return words


def _not_in(keywords: list[str], titles: list[str]) -> list[str]:
    """Keywords that do not occur in any of the titles (a marketer must not drop "marketing" jobs)."""
    return [k for k in keywords if not any(contains_any(t, [k]) for t in titles)]


def experience_limit(profile: CandidateProfile) -> float | None:
    if profile.seniority == "senior":
        return None
    return float(math.ceil(profile.years_experience) + YEARS_MARGIN)


def personalize(cfg: dict[str, Any], profile: CandidateProfile) -> dict[str, Any]:
    """The config this user's run should use. Unchanged unless `auto_from_cv` is on."""
    if not cfg.get("auto_from_cv"):
        return cfg
    search = cfg.get("search", {})
    titles = list(search.get("queries") or []) or list(profile.target_roles)[: search.get("auto_queries", 8)]
    if not titles:
        log.warning("auto_from_cv: no job titles (the CV gave none and search.queries is empty); "
                    "add titles to this user's config.yaml")
        return cfg

    out = copy.deepcopy(cfg)
    out["search"]["queries"] = titles
    out["search"]["employers"] = {}
    out.setdefault("profile", {})["preferences"] = ""
    f = out["filters"]
    junior = profile.seniority in ("student", "junior")
    f["role_keywords"] = role_words(titles)
    f["role_description_keywords"] = []          # the owner's "CS degree" escape hatch
    f["exclude_keywords"] = _not_in(f.get("exclude_keywords") or [], titles)
    f["exclude_exceptions"] = []
    f["senior_keywords"] = _not_in(f.get("senior_keywords") or [], titles)
    f["exclude_senior"] = junior
    f["max_required_years"] = f["junior_max_required_years"] = experience_limit(profile)
    if not junior:
        f["experienced_phrases"] = []            # "proven experience" is fine for an experienced hire
    out.setdefault("agent", {})["role_groups"] = {}
    log.info("auto_from_cv: %d titles, %d role words, experience limit %s", len(titles),
             len(f["role_keywords"]), f["max_required_years"])
    return out
