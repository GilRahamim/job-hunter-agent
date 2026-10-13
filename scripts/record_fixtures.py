"""Record trimmed raw API responses into tests/fixtures/ (run manually when an API changes).

Usage:  python scripts/record_fixtures.py
Diff the JSON keys against the previous fixtures: that diff is the bug report.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobhunter.collectors import ats, remote_boards  # noqa: E402
from jobhunter.collectors.base import get_json, get_session  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
KEEP = 5


def save(name: str, data: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {name}")


def main() -> None:
    gh = get_json(ats.GREENHOUSE_URL.format(slug="jfrog"))
    save("greenhouse_jfrog.json", {**gh, "jobs": gh["jobs"][:KEEP]})

    save("lever_cloudinary.json", get_json(ats.LEVER_URL.format(slug="cloudinary"))[:KEEP])

    ab = get_json(ats.ASHBY_URL.format(slug="moonactive"))
    save("ashby_moonactive.json", {**ab, "jobs": ab["jobs"][:KEEP]})

    sr = get_json(ats.SR_LIST_URL.format(slug="armis", offset=0))
    content = sr["content"][:KEEP]
    save("smartrecruiters_armis.json", {
        **sr, "content": content,
        "details": {i["id"]: get_json(ats.SR_DETAIL_URL.format(slug="armis", id=i["id"]))
                    for i in content[:2]},
    })

    rem = get_json(remote_boards.REMOTIVE_URL.format(category="software-development"))
    save("remotive.json", {**rem, "jobs": rem["jobs"][:KEEP]})

    save("remoteok.json", get_json(remote_boards.REMOTEOK_URL, headers=remote_boards.BROWSER_UA)[:KEEP + 1])

    him = get_json(remote_boards.HIMALAYAS_URL.format(size=20, offset=0))
    save("himalayas.json", {**him, "jobs": him["jobs"][:KEEP]})

    rss = get_session().get(remote_boards.WWR_URL.format(category="remote-back-end-programming-jobs"), timeout=15)
    rss.raise_for_status()
    text = rss.text
    head, *items = text.split("<item>")
    kept = [it.split("</item>")[0] + "</item>" for it in items[:KEEP]]
    save("wwr_backend.rss", head + "".join(f"<item>{it}" for it in kept) + "</channel></rss>")

    arb = get_json(remote_boards.ARBEITNOW_URL.format(page=1))
    save("arbeitnow.json", {"data": [j for j in arb["data"] if j.get("remote")][:KEEP]})


if __name__ == "__main__":
    main()
