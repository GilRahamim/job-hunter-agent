"""Render the running dashboard and put it next to the Figma reference.

Usage (from the project root, with `streamlit run dashboard.py` already running):
    python .claude/skills/dashboard-design/scripts/compare.py
    python .claude/skills/dashboard-design/scripts/compare.py --url http://localhost:8501 --scheme dark \
        --figma .claude/skills/dashboard-design/references/screens/figma-8-27-dark-moody-split.png

Writes to data/design-check/:
    app-<scheme>.png          full-page render of the app
    compare-<scheme>.png      Figma (right) | app (left), same width, for side-by-side review

One-time setup:  pip install playwright pillow && python -m playwright install chromium
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

SKILL = Path(__file__).resolve().parent.parent
DEFAULT_FIGMA = {
    "light": SKILL / "references/screens/figma-2-30-dashboard-jobs.png",
    "dark": SKILL / "references/screens/figma-8-27-dark-moody-split.png",
}


def render(url: str, scheme: str, width: int, out: Path, chrome: str | None) -> Path:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chrome) if chrome else p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": 1400}, color_scheme=scheme)
        page.goto(url, wait_until="networkidle")
        page.wait_for_selector('[data-testid="stAppViewContainer"]', timeout=30_000)
        page.wait_for_timeout(2500)  # fonts, data grid canvas
        path = out / f"app-{scheme}.png"
        page.screenshot(path=str(path), full_page=True)
        browser.close()
    return path


def side_by_side(app_png: Path, figma_png: Path, out: Path, scheme: str) -> Path:
    app, fig = Image.open(app_png).convert("RGB"), Image.open(figma_png).convert("RGB")
    w = max(app.width, fig.width)
    scale = lambda im: im.resize((w, round(im.height * w / im.width))) if im.width != w else im
    app, fig = scale(app), scale(fig)
    canvas = Image.new("RGB", (w * 2 + 24, max(app.height, fig.height) + 40), "white")
    canvas.paste(app, (0, 40))
    canvas.paste(fig, (w + 24, 40))
    d = ImageDraw.Draw(canvas)
    d.text((10, 12), "APP", fill="black")
    d.text((w + 34, 12), f"FIGMA  ({figma_png.name})", fill="black")
    path = out / f"compare-{scheme}.png"
    canvas.save(path)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8501")
    ap.add_argument("--scheme", choices=["light", "dark", "both"], default="both")
    ap.add_argument("--figma", type=Path, help="reference PNG (default: the matching Figma frame)")
    ap.add_argument("--width", type=int, default=1500, help="Figma frame 2:30 is 1500px wide")
    ap.add_argument("--out", type=Path, default=Path("data/design-check"))
    ap.add_argument("--chrome", help="path to a Chrome/Chromium binary, if playwright's is not installed")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    for scheme in (["light", "dark"] if a.scheme == "both" else [a.scheme]):
        app_png = render(a.url, scheme, a.width, a.out, a.chrome)
        ref = a.figma or DEFAULT_FIGMA[scheme]
        print(side_by_side(app_png, ref, a.out, scheme))


if __name__ == "__main__":
    main()
