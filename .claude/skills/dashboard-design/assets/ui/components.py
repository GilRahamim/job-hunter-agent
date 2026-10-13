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

_CSS = (Path(__file__).parent / "theme.css").read_text(encoding="utf-8")


def inject_theme() -> None:
    """Call once at the top of the page, after st.set_page_config."""
    scheme = getattr(getattr(st.context, "theme", None), "type", None) or "light"
    tokens = DARK if scheme == "dark" else LIGHT
    st.html(f"<style>{css_vars(tokens)}\n{_CSS}</style>")


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
