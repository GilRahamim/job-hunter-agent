"""Reusable dashboard pieces matching the Figma components (frame 2:16).

Figma component      → here
Chip/Good, Chip/Gap  → chips(skills, kind)        (st.badge green / red)
Chip/Plain           → chips(skills, "plain")     (st.badge gray)
KPI Card             → kpi_row(items)             (st.metric in .st-key-kpis)
Button/Primary       → st.button(type="primary")
Button/Secondary     → st.button() / st.link_button()
Score box            → score_box(score)
"""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from .tokens import DARK, LIGHT, css_vars

_CSS_PATH = Path(__file__).parent / "theme.css"   # read per run: edits apply without a restart


def current_scheme() -> str:
    """'dark' or 'light', as the browser actually renders it."""
    return getattr(getattr(st.context, "theme", None), "type", None) or "light"


def inject_theme() -> None:
    """Call once at the top of the page, after st.set_page_config."""
    tokens = DARK if current_scheme() == "dark" else LIGHT
    st.html(f"<style>{css_vars(tokens)}\n{_CSS_PATH.read_text(encoding='utf-8')}</style>")


def brand_header() -> None:
    """Sidebar masthead: brand name with the sparkles mark (Figma 7:2430) and the kit badge.

    The mark is a CSS background image: st.html's sanitizer strips inline <svg>."""
    import re
    from urllib.parse import quote

    tokens = DARK if current_scheme() == "dark" else LIGHT
    svg = (Path(__file__).parent / "assets" / "sparkles.svg").read_text(encoding="utf-8")
    svg = re.sub(r'stroke="[^"]*"', f'stroke="{tokens["sb_on_accent"]}"', svg)
    svg = re.sub(r' (style|overflow|preserveAspectRatio)="[^"]*"', "", svg)
    uri = "data:image/svg+xml;utf8," + quote(svg)
    st.html('<div class="jh-brand-row"><span class="jh-kit-badge">ערכת החיפוש שלך</span>'
            '<div class="jh-brand"><span>Job Hunter</span>'
            f'<span class="jh-brand-mark" style="background-image:url(&quot;{uri}&quot;)"></span></div></div>')


def question(text: str, sub: str | None = None) -> None:
    st.html(f'<div class="jh-q">{html.escape(text)}</div>'
            + (f'<div class="jh-q-sub">{html.escape(sub)}</div>' if sub else ""))


def theme_toggle() -> None:
    """Light/dark switch. Streamlit keeps the chosen theme in localStorage; set it and reload."""
    import streamlit.components.v1 as components

    is_dark = current_scheme() == "dark"
    want_dark = st.toggle("מצב כהה", value=is_dark, key="dark_mode")
    if want_dark != is_dark:
        name = "Dark" if want_dark else "Light"
        components.html(
            f"<script>parent.localStorage.setItem('stActiveTheme-/-v2', JSON.stringify('{name}'));"
            "parent.location.reload();</script>", height=0)


def title(text: str) -> None:
    st.html(f'<div class="jh-title">{html.escape(text)}</div>')


def kpi_row(items: list[tuple[str, int | str]]) -> None:
    """items in reading order (right → left in RTL): [("משרות מתאימות", 12), ...]"""
    with st.container(key="kpis", horizontal=True, gap="medium"):
        for label, value in items:
            st.metric(label, value)


def chips(skills: list[str], kind: str = "plain") -> None:
    color = {"good": "green", "gap": "red", "plain": "gray"}[kind]
    with st.container(horizontal=True, gap="small"):
        for s in skills:
            st.badge(s, color=color)


def score_box(score: float) -> None:
    st.html(f'<div class="jh-score">{round(score)}</div>')


def section_label(text: str) -> None:
    st.html(f'<div class="jh-section-label">{html.escape(text)}</div>')
