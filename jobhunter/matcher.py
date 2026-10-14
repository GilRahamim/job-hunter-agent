"""Stage 2 + 3: free pre-score (TF-IDF + skill overlap) and parallel LLM scoring."""
from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from jobhunter.db import now_utc
from jobhunter.filters import required_years
from jobhunter.models import CandidateProfile, Job, JobMatch
from jobhunter.prompts import SCORE_SYSTEM, SCORE_USER
from jobhunter.skills import extract_skills

log = logging.getLogger(__name__)

W_TFIDF, W_SKILLS = 0.6, 0.4
SKILL_DENOM_CAP = 15
MAX_DESCRIPTION_CHARS = 6000
LLM_ATTEMPTS = 3
BACKOFF_SECONDS = 1.0                 # doubled on each retry; tests set it to 0


def prescore(profile: CandidateProfile, jobs: list[Job]) -> list[float]:
    """Ranking signal in [0, 100] for each job; no API cost."""
    if not jobs:
        return []
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [profile.as_text()] + [j.text() for j in jobs]
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True,
                                 stop_words="english").fit_transform(texts)
        sims = cosine_similarity(matrix[0], matrix[1:]).ravel()
    except ValueError:                           # empty vocabulary
        sims = [0.0] * len(jobs)
    lo, hi = min(sims), max(sims)
    normalized = [(s - lo) / (hi - lo) if hi > lo else float(s) for s in sims]

    cv_skills = {s.lower() for s in profile.skills}
    scores = []
    for job, tfidf in zip(jobs, normalized):
        text = f"{job.title}\n{job.description}"
        job_skills = {s.lower() for s in extract_skills(text)}
        overlap = min(1.0, len(cv_skills & job_skills) / max(1, min(len(job_skills), SKILL_DENOM_CAP)))
        gap = required_years(text) - (profile.years_experience + 2)
        penalty = min(25.0, 5 * gap) if gap > 0 else 0.0
        scores.append(max(0.0, min(100.0, 100 * (W_TFIDF * tfidf + W_SKILLS * overlap) - penalty)))
    return scores


def select_for_llm(scores: list[float], cfg: dict[str, Any]) -> list[int]:
    """Indexes of the best jobs by pre-score that clear the threshold, capped at llm_top_n."""
    m = cfg["matching"]
    eligible = [i for i, s in enumerate(scores) if s >= m["min_prescore_for_llm"]]
    eligible.sort(key=lambda i: scores[i], reverse=True)
    return eligible[: m["llm_top_n"]]


def explanation_language(cfg: dict[str, Any]) -> str:
    """The language the LLM writes its reasons in (profile.explanation_language: he / en)."""
    return "Hebrew" if cfg.get("profile", {}).get("explanation_language", "he") == "he" else "English"


def build_messages(profile: CandidateProfile, job: Job, cfg: dict[str, Any]) -> list[tuple[str, str]]:
    remote_note = f"(remote; region: {job.remote_region or 'unspecified'})" if job.is_remote else ""
    user = SCORE_USER.format(
        headline=profile.headline, seniority=profile.seniority,
        years_experience=profile.years_experience, skills=", ".join(profile.skills),
        projects="; ".join(profile.projects), education="; ".join(profile.education),
        title=job.title, company=job.company, location=job.location, remote_note=remote_note,
        description=job.description[:MAX_DESCRIPTION_CHARS])
    return [("system", SCORE_SYSTEM.format(language=explanation_language(cfg))), ("user", user)]


def _score_one(structured: Any, messages: list[tuple[str, str]], title: str,
               errors: list[str]) -> JobMatch | None:
    for attempt in range(LLM_ATTEMPTS):
        try:
            result = structured.invoke(messages)
            return result if isinstance(result, JobMatch) else JobMatch(**result)
        except Exception as e:  # noqa: BLE001 - rate limits and validation errors are retried
            log.warning("LLM scoring %r failed (attempt %d/%d): %s", title, attempt + 1, LLM_ATTEMPTS, e)
            if attempt < LLM_ATTEMPTS - 1:
                time.sleep(BACKOFF_SECONDS * 2 ** attempt)
            else:
                errors.append(f"{type(e).__name__}: {e}")
    return None


def llm_score(llm: Any, profile: CandidateProfile, jobs: list[Job],
              cfg: dict[str, Any], errors: list[str] | None = None) -> list[JobMatch | None]:
    """One JobMatch per job (None when all retries failed). Order matches `jobs`.
    The last error of each failed job is appended to `errors` when given."""
    errors = [] if errors is None else errors
    if not jobs:
        return []
    structured = llm.with_structured_output(JobMatch)
    with ThreadPoolExecutor(max_workers=cfg["llm"].get("max_workers", 6)) as pool:
        futures = [pool.submit(_score_one, structured, build_messages(profile, j, cfg), j.title, errors)
                   for j in jobs]
        return [f.result() for f in futures]


def scored_row(job: Job, pre: float, match: JobMatch | None, cv_hash: str, model: str) -> dict[str, Any]:
    """DB row: the posting plus its scoring fields. score = LLM score when present."""
    row = job.to_dict()
    years = required_years(f"{job.title}\n{job.description}")
    row.update(prescore=round(pre, 1), cv_hash=cv_hash, scored_at=now_utc(), required_years=years)
    if match:
        row.update(score=float(match.score), verdict=match.verdict, seniority_fit=match.seniority_fit,
                   required_years=years if match.required_years is None else match.required_years,
                   matching_skills=match.matching_skills, missing_skills=match.missing_skills,
                   reasons=match.reasons, cv_tip=match.cv_tip, scored_by=f"llm:{model}")
    else:
        # clear an earlier LLM verdict: it no longer belongs to this score (CV changed or the call failed)
        row.update(score=round(pre, 1), scored_by="heuristic", verdict=None, seniority_fit=None,
                   matching_skills=None, missing_skills=None, reasons=None, cv_tip=None)
    return row
