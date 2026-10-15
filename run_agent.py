"""CLI entry point of the search agent:  python run_agent.py [--no-llm] [--sources ats,remotive] ..."""
from __future__ import annotations

import argparse
import logging
import os
import runpy
import sys
from datetime import datetime

from jobhunter.config import ROOT, run_dir


def setup_logging() -> None:
    log_dir = run_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    file = logging.FileHandler(log_dir / f"run-{datetime.now():%Y%m%d-%H%M}.log", encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.handlers[:] = [console, file]
    for noisy in ("urllib3", "httpx", "httpcore", "JobSpy", "anthropic", "langsmith", "matplotlib"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def source_status(h: dict) -> str:
    """'ok', the error, or the note of a source that was skipped or partly missed."""
    if h["error"]:
        return f"ERROR: {h['error']}"
    return f"ok (note: {h['warning']})" if h.get("warning") else "ok"


def print_summary(state: dict, top: int) -> None:
    stats = state["stats"]
    print("\n=== Run summary ===")
    print(f"mode: {stats['mode']} | duration: {stats['duration_s']}s"
          f"{' | DRY RUN (nothing saved)' if stats['dry_run'] else ''}")
    for h in state["health"]:
        print(f"  {h['source']:<16}{h['fetched']:>5} jobs  {source_status(h)}")
    print(f"collected {stats['collected']} | new {stats['new']} | already known {stats['known']}")
    print(f"filter drops: {stats['filtered_by_reason'] or 'none'} -> kept {stats['kept']}")
    print(f"scored: {stats['prescored']} (rescored {stats['rescored']}, llm {stats['llm_scored']}, "
          f"llm failed {stats['llm_failed']})")
    rows = sorted(state["rows"], key=lambda r: r["score"], reverse=True)[:top]
    if rows:
        print(f"\nTop {len(rows)}:")
        for r in rows:
            print(f"  {r['score']:5.1f} | {r['title']} | {r['company']} | {r['location'] or r['remote_region']}")


def print_agent_summary(result: dict, top: int) -> None:
    stats = result["stats"]
    print("\n=== Agent run summary ===")
    print(f"mode: {stats['mode']} | stopped: {stats['stop_reason']} | steps: {stats['steps']} | "
          f"duration: {stats['duration_s']}s{' | DRY RUN (nothing saved)' if stats['dry_run'] else ''}")
    for h in result["health"]:
        print(f"  {h['source']:<16}{h['fetched']:>5} jobs  {source_status(h)}")
    print(f"searches {stats['searches']} | collected {stats['collected']} | "
          f"new after filters {stats['kept']} | read {stats['read']}")
    print(f"filter drops: {stats['filtered_by_reason'] or 'none'}")
    print(f"saved matches: {stats['agent_matches']} ({stats['strong_matches']} at or above the goal score)")
    rows = sorted((r for r in result["rows"] if r["scored_by"].startswith("agent:")),
                  key=lambda r: r["score"], reverse=True)[:top]
    for r in rows:
        print(f"  {r['score']:5.1f} | {r['title']} | {r['company']} | {r['location'] or r['remote_region']}")
        print(f"        {r['reasons']}")


def run_agent_loop(args: argparse.Namespace) -> int:
    from jobhunter import agent_loop
    from jobhunter.runlock import RunLocked, run_lock

    try:
        with run_lock():
            result = agent_loop.run(goal=args.goal, max_steps=args.max_steps, dry_run=args.dry_run)
    except RunLocked as e:
        print(e)
        return 2
    except agent_loop.AgentUnavailable as e:
        print(e)
        return 1
    except Exception as e:  # noqa: BLE001 - report and exit non-zero
        logging.getLogger("run_agent").error("agent failed: %s", e)
        return 1
    print_agent_summary(result, 15)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect, filter and score job postings")
    parser.add_argument("--no-llm", action="store_true", help="heuristic scores only (free)")
    parser.add_argument("--sources", help="comma-separated collectors, e.g. ats,remotive")
    parser.add_argument("--limit", type=int, help="cap jobs per source (per company for ats)")
    parser.add_argument("--rescore", action="store_true", help="re-score existing jobs against the current CV")
    parser.add_argument("--dry-run", action="store_true", help="do not write to the DB; show the top 15")
    parser.add_argument("--check-companies", action="store_true", help="validate companies.yaml and exit")
    parser.add_argument("--agent", action="store_true",
                        help="tool-using agent: the LLM writes the searches and picks the matches")
    parser.add_argument("--goal", type=int, help="with --agent: matches to find (default agent.goal_matches)")
    parser.add_argument("--max-steps", type=int, help="with --agent: model turns (default agent.max_steps)")
    parser.add_argument("--user", help="search for a user added in the dashboard (folder name under users/); "
                                       "default: the owner (cv/, data/, config.yaml)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.user:
        from jobhunter.users import list_users
        if args.user not in list_users():
            print(f"unknown user {args.user!r}; known: {', '.join(list_users()) or 'none'}")
            return 2
        os.environ["JOBHUNTER_USER"] = args.user       # every path and the config follow this user

    if args.check_companies:
        sys.argv = ["check_boards.py", str(ROOT / "companies.yaml")]
        runpy.run_path(str(ROOT / "scripts" / "check_boards.py"), run_name="__main__")
        return 0

    setup_logging()
    if args.agent:
        return run_agent_loop(args)
    from jobhunter import agent
    from jobhunter.runlock import RunLocked, run_lock

    try:
        with run_lock():
            state = agent.run(
                no_llm=args.no_llm, limit=args.limit, rescore=args.rescore, dry_run=args.dry_run,
                sources=[s.strip() for s in args.sources.split(",") if s.strip()] if args.sources else None)
    except RunLocked as e:
        print(e)
        return 2
    except Exception as e:  # noqa: BLE001 - report and exit non-zero
        logging.getLogger("run_agent").error("run failed: %s", e)
        return 1

    print_summary(state, 15 if args.dry_run else 10)
    health = state["health"]
    if health and all(h["error"] and not h["fetched"] for h in health):
        print("\nEvery source failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
