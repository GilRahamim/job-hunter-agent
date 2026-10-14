"""Validate companies.yaml: which ATS slugs are alive and how many Israel jobs each has.

Usage:  python scripts/check_boards.py [path/to/companies.yaml]
        python scripts/check_boards.py --probe acme acmeio   # try new slugs on every ATS
"""
from __future__ import annotations

import concurrent.futures as cf
import re
import sys

import requests
import yaml

IL = re.compile(
    r"israel|tel[\s-]?aviv|herzliya|haifa|jerusalem|petah|ramat[\s-]?gan|be'?er[\s-]?sheva|netanya|"
    r"ra'?anana|rehovot|yokneam|caesarea|hod[\s-]?hasharon|kfar[\s-]?saba|modiin|rosh[\s-]?ha|"
    r"ישראל|תל אביב|ירושלים|חיפה|הרצליה",
    re.I,
)
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (JobHunterAgent)"


def greenhouse(slug):
    js = S.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=15)
    js.raise_for_status()
    jobs = js.json()["jobs"]
    return len(jobs), sum(bool(IL.search((j.get("location") or {}).get("name", ""))) for j in jobs)


def lever(slug):
    from jobhunter.collectors.ats import fetch_lever      # also finds EU accounts (jobs.eu.lever.co)
    jobs = fetch_lever(slug)
    return len(jobs), sum(bool(IL.search(j.location)) for j in jobs)


def ashby(slug):
    r = S.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    r.raise_for_status()
    jobs = r.json()["jobs"]
    loc = lambda j: (j.get("location") or "") + " " + " ".join(s.get("location", "") for s in j.get("secondaryLocations") or [])
    return len(jobs), sum(bool(IL.search(loc(j))) for j in jobs)


def smartrecruiters(slug):
    r = S.get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100", timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("totalFound", 0), sum((j.get("location") or {}).get("country", "").lower() == "il" for j in d.get("content", []))


def workday(entry):
    # entry: {"tenant": "intel", "wd": "wd1", "site": "External"}; Israel = the collector's location facet
    from jobhunter.collectors.ats import WORKDAY_BASE, _workday_search, israel_facets
    base = WORKDAY_BASE.format(**entry)
    first = _workday_search(base, {}, 0)
    facets = israel_facets(first)
    return first.get("total", 0), _workday_search(base, facets, 0).get("total", 0) if facets else 0


def comeet(entry):
    # entry: "<slug>/<uid>" from https://www.comeet.com/jobs/<slug>/<uid>
    from jobhunter.collectors.ats import fetch_comeet
    jobs = fetch_comeet(entry)
    return len(jobs), sum(bool(IL.search(j.location)) for j in jobs)


ATS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters,
       "workday": workday, "comeet": comeet}


def label(slug):
    return slug["tenant"] if isinstance(slug, dict) else slug


def check(ats, slug):
    try:
        total, il = ATS[ats](slug)
        return ats, slug, total, il, None
    except Exception as e:  # noqa: BLE001 — report, don't crash
        return ats, slug, 0, 0, type(e).__name__ + ": " + str(e)[:60]


def main():
    args = sys.argv[1:]
    if args and args[0] == "--probe":
        tasks = [(a, s) for s in args[1:] for a in ATS if a not in ("workday", "comeet")]  # need tenant / uid
    else:
        path = args[0] if args else "companies.yaml"
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        tasks = [(a, s) for a, slugs in cfg.items() if a in ATS for s in slugs or []]

    with cf.ThreadPoolExecutor(12) as ex:
        results = list(ex.map(lambda t: check(*t), tasks))

    print(f"{'ATS':<16}{'slug':<22}{'jobs':>6}{'israel':>8}  status")
    for ats, slug, total, il, err in sorted(results, key=lambda r: (r[4] is not None, -r[3])):
        if args and args[0] == "--probe" and err:
            continue
        print(f"{ats:<16}{label(slug):<22}{total:>6}{il:>8}  {'OK' if not err else err}")
    dead = [r for r in results if r[4]]
    if dead and not (args and args[0] == "--probe"):
        print(f"\n{len(dead)} dead slug(s) — remove or fix them in companies.yaml")


if __name__ == "__main__":
    main()
