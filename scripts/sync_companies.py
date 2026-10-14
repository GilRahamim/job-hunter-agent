"""Add Israeli companies' job boards to companies.yaml from the open Israeli Tech Map dataset
and the venture-capital portfolio boards (Getro) listed in config.yaml.

Source: https://github.com/mluggy/techmap (ODbL v1.0, (c) Michael Luggy and contributors): ~8,000
Israeli companies, some with their Comeet / Greenhouse / Lever ids or a careers page, plus daily job
lists whose links reveal more Comeet boards.

Every candidate board is fetched with the collectors' own code and kept only when it has at least
one job in Israel, so companies.yaml only gains boards the daily run can actually read.

Usage:  python scripts/sync_companies.py                 # ids + job links (~2 min)
        python scripts/sync_companies.py --scan-careers  # also open ~1,300 careers pages (~10 min)
        python scripts/sync_companies.py --dry-run       # print what would be added
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jobhunter.collectors import ats, getro  # noqa: E402
from jobhunter.collectors.base import get_session  # noqa: E402
from jobhunter.config import load_config  # noqa: E402
from jobhunter.filters import is_israel  # noqa: E402

TECHMAP_ZIP = "https://codeload.github.com/mluggy/techmap/zip/refs/heads/main"
COMPANIES_YAML = ROOT / "companies.yaml"
BOARD_PATTERNS = {                    # careers links / pages -> (ats, entry)
    "comeet": re.compile(r"comeet\.com/jobs/([\w-]+)/([0-9A-Fa-f]{2}\.[0-9A-Fa-f]{3})"),
    "greenhouse": re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)"),
    "lever": re.compile(r"jobs\.(?:eu\.)?lever\.co/([\w-]+)"),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([\w.-]+)"),            # "monday.com" is a real slug
}
_SKIP_SLUGS = {"embed", "js", "jobs", "api", "v1"}


def download_techmap() -> zipfile.ZipFile:
    resp = get_session().get(TECHMAP_ZIP, timeout=300)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def boards_in(text: str) -> set[tuple[str, str]]:
    found = set()
    for kind, rx in BOARD_PATTERNS.items():
        for m in rx.finditer(text):
            if kind == "comeet":
                found.add((kind, f"{m.group(1).lower()}/{m.group(2).upper()}"))
            elif m.group(1).lower() not in _SKIP_SLUGS:
                found.add((kind, m.group(1).lower()))
    return found


def candidates(z: zipfile.ZipFile) -> tuple[set[tuple[str, str]], list[str]]:
    """Boards named in the company files and job links, and the careers pages to scan."""
    found: set[tuple[str, str]] = set()
    pages: list[str] = []
    for name in z.namelist():
        if "/companies/" in name and name.endswith(".json"):
            c = json.loads(z.read(name))
            if not c.get("isActive", True):
                continue
            if c.get("comeetId"):
                found |= boards_in(f"comeet.com/jobs/{c['comeetId']}")
            if c.get("greenhouseId"):
                found.add(("greenhouse", c["greenhouseId"].lower()))
            if c.get("leverId"):
                found.add(("lever", c["leverId"].lower()))
            url = c.get("careersUrl") or ""
            hits = boards_in(url)
            found |= hits
            if url and not hits:
                pages.append(url)
        elif "/jobs/" in name and name.endswith(".csv"):
            for row in csv.DictReader(io.StringIO(z.read(name).decode("utf-8-sig"))):
                found |= boards_in(row.get("url") or "")
    return found, pages


def vc_board_links(cfg: dict) -> set[tuple[str, str]]:
    """Boards behind the Israel jobs on the VC portfolio boards (sources.getro in config.yaml)."""
    found: set[tuple[str, str]] = set()
    for board in (cfg.get("sources", {}).get("getro") or {}).get("boards") or []:
        try:
            for job in getro.fetch_board(board["id"]):
                found |= boards_in(job.url)
        except Exception as e:  # noqa: BLE001
            print(f"  {board.get('name')}: {type(e).__name__}")
    return found


def scan_page(url: str) -> set[tuple[str, str]]:
    try:
        resp = get_session().get(url, timeout=15, headers=ats.BROWSER_UA)
        return boards_in(resp.url + "\n" + resp.text)
    except Exception:  # noqa: BLE001 - dead careers pages are common
        return set()


def israel_jobs(board: tuple[str, str]) -> int:
    kind, entry = board
    try:
        return sum(is_israel(j.location) for j in ats.FETCHERS[kind](entry))
    except Exception:  # noqa: BLE001
        return 0


def existing(text: str) -> set[tuple[str, str]]:
    have, section = set(), None
    for line in text.splitlines():
        if re.match(r"^[a-z]+:\s*$", line):
            section = line.split(":")[0]
        elif section and (m := re.match(r"^\s+-\s+([^#\s{][^#\s]*)", line)):
            have.add((section, m.group(1).lower()))
    return have


def add_to_yaml(text: str, new: dict[str, list[str]]) -> str:
    """Append entries at the end of each ATS section (creating missing sections), keeping comments."""
    lines = text.rstrip("\n").splitlines()
    for kind, entries in new.items():
        if not entries:
            continue
        header = next((i for i, ln in enumerate(lines) if ln.startswith(f"{kind}:")), None)
        block = [f"  - {e}" for e in sorted(entries)]
        if header is None:
            lines += ["", f"{kind}:   # added by scripts/sync_companies.py (Israeli Tech Map, ODbL)", *block]
            continue
        end = header + 1
        while end < len(lines) and (lines[end].startswith("  ") or not lines[end].strip()):
            end += 1
        while end > header + 1 and not lines[end - 1].strip():
            end -= 1
        lines[end:end] = [f"  # added by scripts/sync_companies.py (Israeli Tech Map, ODbL)", *block]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scan-careers", action="store_true", help="also open each careers page")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.disable(logging.WARNING)

    print("downloading the Israeli Tech Map dataset...")
    found, pages = candidates(download_techmap())
    print("reading the VC portfolio boards (Getro) for the job platforms their links point to...")
    found |= vc_board_links(load_config())
    if args.scan_careers:
        print(f"scanning {len(pages)} careers pages...")
        with ThreadPoolExecutor(16) as pool:
            for hits in pool.map(scan_page, pages):
                found |= hits
    text = COMPANIES_YAML.read_text(encoding="utf-8")
    have = existing(text)
    todo = sorted(b for b in found if (b[0], b[1].lower()) not in have)
    print(f"{len(found)} boards named, {len(todo)} not in companies.yaml yet; checking which are live...")
    with ThreadPoolExecutor(12) as pool:
        counts = list(pool.map(israel_jobs, todo))
    live = [(b, n) for b, n in zip(todo, counts) if n]
    new: dict[str, list[str]] = {}
    for (kind, entry), n in sorted(live, key=lambda x: -x[1]):
        print(f"  + {kind:<11}{entry:<36}{n:>4} Israel jobs")
        new.setdefault(kind, []).append(entry)
    print(f"{len(live)} live boards with Israel jobs ({sum(n for _, n in live)} jobs); "
          f"{len(todo) - len(live)} dead or without Israel jobs skipped")
    if live and not args.dry_run:
        COMPANIES_YAML.write_text(add_to_yaml(text, new), encoding="utf-8")
        print(f"companies.yaml updated. Validate any time with: python run_agent.py --check-companies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
