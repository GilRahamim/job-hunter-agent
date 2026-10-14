"""Dedupe: the same posting (same id) or the same role on several boards (same company|title key).
Shared by the fixed pipeline and the agent loop."""
from __future__ import annotations

from jobhunter.models import Job

_COMPANY_BOARDS = ("greenhouse", "lever", "ashby", "smartrecruiters", "workday", "comeet")


def source_priority(source: str) -> int:
    """Lower is better: company boards (full descriptions) beat JobSpy beat remote boards."""
    if source in _COMPANY_BOARDS:
        return 0
    if source.startswith("jobspy"):
        return 1
    return 2


def dedupe_batch(jobs: list[Job]) -> list[Job]:
    """Drop repeated ids; for the same company|title keep the best source (board > jobspy > remote)."""
    by_id = {j.id: j for j in jobs}
    best: dict[str, Job] = {}
    unkeyed: list[Job] = []
    for job in by_id.values():
        if not job.company.strip():
            unkeyed.append(job)       # without a company the key would merge unrelated roles
            continue
        cur = best.get(job.dedupe_key)
        rank = (source_priority(job.source), -len(job.description))
        if cur is None or rank < (source_priority(cur.source), -len(cur.description)):
            best[job.dedupe_key] = job
    return [*best.values(), *unkeyed]


def is_new(job: Job, known_ids: set[str], known_keys: set[str]) -> bool:
    """Not stored yet, neither as this posting nor as the same role from another board."""
    return job.id not in known_ids and (not job.company.strip() or job.dedupe_key not in known_keys)
