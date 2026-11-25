"""Find company job boards with Google `site:` searches (through SerpAPI) and check they are live.

A query like `site:comeet.com/jobs junior ai engineer israel` returns individual postings on the
ATS (Comeet, Greenhouse, Lever, Ashby). Each result link names the company's board, so this finds
companies that are not in companies.yaml yet. Every board is then fetched with the collectors' own
code and kept only when it has at least one job in Israel.

The queries live in config.yaml (`sources.discover_boards.queries`). Each one is one paid SerpAPI
search, and they share the monthly quota with the daily Google Jobs source.

Usage:  python scripts/discover_boards.py           # print the boards that would be added
        python scripts/discover_boards.py --write   # also append them to companies.yaml
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from jobhunter.collectors.base import get_json  # noqa: E402
from jobhunter.collectors.board_search import boards_in, group_dorks  # noqa: E402
from jobhunter.collectors.serpapi import SERPAPI_URL  # noqa: E402
from jobhunter.config import load_config, load_env  # noqa: E402
from sync_companies import COMPANIES_YAML, add_to_yaml, existing, israel_jobs  # noqa: E402


def search_links(query: str, key: str, num: int = 100) -> list[str]:
    """Result links of one Google search (one SerpAPI call). Errors give an empty list."""
    try:
        data = get_json(SERPAPI_URL, params={"engine": "google", "q": query, "num": num,
                                             "hl": "en", "api_key": key})
    except Exception as e:  # noqa: BLE001 - one failed query must not stop the others
        print(f"  {query[:60]!r}: {type(e).__name__}")
        return []
    return [r["link"] for r in data.get("organic_results", []) if r.get("link")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="append the live boards to companies.yaml")
    parser.add_argument("--limit", type=int, help="run only the first N queries (saves quota)")
    parser.add_argument("--groups", action="store_true",
                        help="also run one search per agent role group over every ATS domain")
    parser.add_argument("--links", help="read result links from this text file ('-' = stdin) instead of "
                                        "calling SerpAPI, e.g. links an agent's web search returned")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.disable(logging.WARNING)

    found: set[tuple[str, str]] = set()
    if args.links:
        raw = sys.stdin.read() if args.links == "-" else Path(args.links).read_text(encoding="utf-8")
        found = boards_in(raw)
        print(f"{len(found)} boards named in the links")
    else:
        load_env()
        key = os.environ.get("SERPAPI_API_KEY")
        if not key:
            print("SERPAPI_API_KEY is not set in .env (or pass --links FILE)")
            return 1
        config = load_config()
        queries = list((config.get("sources", {}).get("discover_boards") or {}).get("queries") or [])
        if args.groups:
            queries += group_dorks(config)
        if not queries:
            print("no queries: add them under sources.discover_boards.queries in config.yaml, or use --groups")
            return 1
        for query in queries[: args.limit or len(queries)]:
            links = search_links(query, key)
            hits = {b for link in links for b in boards_in(link)}
            print(f"{query[:70]!r}: {len(links)} results, {len(hits)} boards")
            found |= hits

    text = COMPANIES_YAML.read_text(encoding="utf-8")
    have = existing(text)
    todo = sorted(b for b in found if (b[0], b[1].lower()) not in have)
    print(f"{len(found)} boards found, {len(todo)} not in companies.yaml yet; checking which are live...")
    with ThreadPoolExecutor(8) as pool:
        counts = list(pool.map(israel_jobs, todo))
    new: dict[str, list[str]] = {}
    for (kind, entry), n in sorted(zip(todo, counts), key=lambda x: -x[1]):
        if n:
            print(f"  + {kind:<11}{entry:<36}{n:>4} Israel jobs")
            new.setdefault(kind, []).append(entry)
    live = sum(len(v) for v in new.values())
    print(f"{live} live boards with Israel jobs; {len(todo) - live} dead or without Israel jobs skipped")
    if live and args.write:
        COMPANIES_YAML.write_text(add_to_yaml(text, new), encoding="utf-8")
        print("companies.yaml updated. Validate any time with: python run_agent.py --check-companies")
    elif live:
        print("dry run: add --write to append them to companies.yaml")
    return 0


if __name__ == "__main__":
    sys.exit(main())
