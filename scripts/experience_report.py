"""Which stored jobs ask for more experience than config.yaml allows, and how each one got in.

For every such job: where it was scraped (source), who scored it (scored_by), the years found and
who found them. "rules" = the regex in filters.py reads them in the stored description (the job was
saved before the current rules); "llm" = only the language model read them.

  scored_by  llm:<model>    the regular search, scored by the LLM
             heuristic      the regular search without an LLM, or a job the smart agent saw but did not save
             agent:<model>  saved by the smart agent

Usage:  python scripts/experience_report.py               # the owner's DB
        python scripts/experience_report.py --user dana   # someone added in the dashboard
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobhunter import db  # noqa: E402
from jobhunter.config import load_config  # noqa: E402
from jobhunter.filters import junior_reason, required_years, years_over_limit  # noqa: E402
from jobhunter.models import CandidateProfile, Job  # noqa: E402
from jobhunter.personalize import personalize  # noqa: E402


def report(cfg: dict, path: Path) -> list[dict]:
    out = []
    for r in db.all_jobs(path=path):
        job = Job("", r["title"] or "", "", "", description=r["description"] or "")
        reason = junior_reason(job, cfg)
        stored = r["required_years"]
        if not reason and not years_over_limit(job, stored, cfg):
            continue
        rules = required_years(f"{job.title}\n{job.description}")
        found_by = "rules" if reason else "llm"
        out.append({"id": r["id"], "title": r["title"], "company": r["company"], "source": r["source"],
                    "scored_by": r["scored_by"] or "-", "first_seen": (r["first_seen"] or "")[:10],
                    "years": stored if found_by == "llm" else rules, "why": reason or "experience",
                    "found_by": found_by, "status": r["status"]})
    return sorted(out, key=lambda x: x["first_seen"], reverse=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--user", default="", help="a person added in the dashboard (default: the owner)")
    args = ap.parse_args()
    path = db.db_path(user=args.user)
    cfg, latest = load_config(args.user), db.latest_profile(path)
    if latest:                                  # the same limits the dashboard uses for this person
        cfg = personalize(cfg, CandidateProfile(**latest["data"]))
    rows = report(cfg, path)
    print(f"{len(rows)} stored jobs are over the experience limit "
          f"(max_required_years: {cfg['filters'].get('max_required_years')})\n")
    for x in rows:
        years = f"{x['years']:g}y" if x["years"] else "-"
        print(f"{x['first_seen']}  {years:>4}  {x['why']:<10} by {x['found_by']:<5}  {x['source']:<18} "
              f"{x['scored_by']:<28} {x['status']:<12} {x['title']} @ {x['company']}")


if __name__ == "__main__":
    main()
