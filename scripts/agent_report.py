"""How good are the smart agent's picks, judged by what you did with them in the dashboard?

Jobs are grouped by who picked them (scored_by) and, for the agent and the regular search, by score
(at or above agent.min_match_score, or below) and by role group (agent.role_groups, from the title).

  pursued    you marked interested / applied / interview / offer, or rejected (you applied; they said no)
  dismissed  you marked not relevant
  open       still "new": you have not judged it yet
  precision  pursued / (pursued + dismissed): of the jobs you judged, the share worth pursuing

Few judged jobs mean a noisy precision, so look at "judged" before comparing.

Usage:  python scripts/agent_report.py                      # the owner's DB
        python scripts/agent_report.py --since 2026-10-01   # jobs first seen on or after this date
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobhunter import db  # noqa: E402
from jobhunter.agent_loop.tools import query_groups  # noqa: E402
from jobhunter.config import load_config  # noqa: E402

PURSUED = (*db.LIKED_STATUSES, "rejected")


def picked_by(scored_by: str | None) -> str:
    """agent (saved by the agent, scored or not) / regular (LLM-scored) / heuristic (no LLM score;
    includes jobs the agent saw but skipped)."""
    s = scored_by or ""
    return "agent" if s.startswith("agent:") else "regular" if s.startswith("llm:") else "heuristic"


def outcome(status: str | None) -> str:
    return "pursued" if status in PURSUED else "dismissed" if status in db.DISLIKED_STATUSES else "open"


def summarize(rows: list[dict]) -> dict:
    """{"jobs", "pursued", "dismissed", "open", "judged", "precision" (None when nothing was judged)}."""
    c = Counter(outcome(r["status"]) for r in rows)
    judged = c["pursued"] + c["dismissed"]
    return {"jobs": len(rows), "pursued": c["pursued"], "dismissed": c["dismissed"], "open": c["open"],
            "judged": judged, "precision": c["pursued"] / judged if judged else None}


def report(cfg: dict, path: Path | str | None = None, since: str = "") -> dict[str, list[tuple[str, dict]]]:
    """Sections of (label, summary): by picker, by picker and score band, agent jobs by role group."""
    rows = [r for r in db.all_jobs(path=path) if (r["first_seen"] or "") >= since]
    min_score = cfg["agent"]["min_match_score"]
    groups = cfg["agent"].get("role_groups") or {}
    by: dict[str, dict[str, list[dict]]] = {"picker": {}, "band": {}, "group": {}}
    for r in rows:
        who = picked_by(r["scored_by"])
        by["picker"].setdefault(who, []).append(r)
        if who != "heuristic" and r["scored_by"] not in db.HEURISTIC_SCORED_BY:   # bands of LLM scores only
            band = f">= {min_score}" if (r["score"] or 0) >= min_score else f"< {min_score}"
            by["band"].setdefault(f"{who} {band}", []).append(r)
        if who == "agent":
            for g in query_groups(r["title"] or "", groups) or ["(no group)"]:
                by["group"].setdefault(g, []).append(r)
    order = {"agent": 0, "regular": 1, "heuristic": 2}
    return {
        "picker": sorted(((k, summarize(v)) for k, v in by["picker"].items()), key=lambda x: order[x[0]]),
        "band": sorted((k, summarize(v)) for k, v in by["band"].items()),
        "group": sorted(((k, summarize(v)) for k, v in by["group"].items()),
                        key=lambda x: (-(x[1]["precision"] or 0), -x[1]["judged"])),
    }


def line(label: str, s: dict) -> str:
    precision = f"{s['precision']:.0%}" if s["precision"] is not None else "-"
    return (f"  {label:<28}{s['jobs']:>6}{s['judged']:>8}{s['pursued']:>9}{s['dismissed']:>11}"
            f"{s['open']:>7}{precision:>11}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="", help="only jobs first seen on or after this date (YYYY-MM-DD)")
    args = ap.parse_args()
    sections = report(load_config(), since=args.since)
    head = f"  {'':<28}{'jobs':>6}{'judged':>8}{'pursued':>9}{'dismissed':>11}{'open':>7}{'precision':>11}"
    titles = {"picker": "Who picked the job", "band": "By score", "group": "Agent picks by role group"}
    for key, title in titles.items():
        print(f"\n{title}\n{head}")
        for label, s in sections[key] or [("(none)", summarize([]))]:
            print(line(label, s))


if __name__ == "__main__":
    main()
