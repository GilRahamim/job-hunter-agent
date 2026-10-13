"""python -m jobhunter.collectors --source ats --limit 5"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter

from jobhunter.collectors import SOURCE_NAMES, collect_all
from jobhunter.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run collectors and print what they found")
    parser.add_argument("--source", action="append", choices=SOURCE_NAMES,
                        help="source to run (repeatable); default = all enabled in config.yaml")
    parser.add_argument("--limit", type=int, default=None,
                        help="max jobs per source (per company for ats)")
    parser.add_argument("--show", type=int, default=3, help="sample jobs to print per source")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # Hebrew titles on Windows consoles
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    results, health = collect_all(load_config(), args.source, args.limit)
    for res, h in zip(results, health):
        companies = Counter(j.company for j in res.jobs)
        print(f"\n== {res.source}: {len(res.jobs)} jobs, {len(companies)} companies/boards, "
              f"{h['duration_s']}s" + (f"  ERROR: {res.error}" if res.error else ""))
        for job in res.jobs[:args.show]:
            print(f"  - [{job.source}] {job.title} @ {job.company} | {job.location} | "
                  f"{job.date_posted} | desc={len(job.description)} chars\n    {job.url}")


if __name__ == "__main__":
    main()
