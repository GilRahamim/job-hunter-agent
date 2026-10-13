"""Design tokens from Figma file xqkcOg1yGvJWFKwS14sEqf (Job Hunter Dashboard).

Single source of truth for anything .streamlit/config.toml cannot express.
Keep the two in sync: config.toml colors == these values.

LIGHT = "Sea"        — frame 2:30 "Dashboard / Jobs"; the sb_* tokens come from "Playful career toolkit" (7:2424)
DARK  = "Teal Night" — deep green-charcoal with a mint accent (replaces the old violet "Night")
"""

LIGHT = {
    "ink": "#16232b",        # color/ink          — primary text
    "slate": "#51636b",      # color/slate        — secondary text, labels
    "accent": "#0f766e",     # color/sea          — primary actions, score, active tab
    "on_accent": "#ffffff",  # text on the accent color
    "line": "#d5dedb",       # color/line         — borders, rules
    "mist": "#e6ecea",       # color/mist         — KPI cards, table header
    "bg": "#f4f6f5",         # color/bg           — page
    "surface": "#ffffff",    # color/surface      — cards, inputs
    "good_bg": "#d6efea", "good_text": "#0b5a53",   # color/chip-good-*
    "gap_bg": "#f6dad6", "gap_text": "#8e2f26",     # color/chip-gap-*
    "kpi_bg": "#e6ecea", "kpi_border": "0", "kpi_radius": "10px", "kpi_shadow": "none",
    # sidebar: Playful career toolkit
    "sb_bg": "#f5f1ff", "sb_card": "#ffffff", "sb_ink": "#282045", "sb_muted": "#706581",
    "sb_line": "#d9cfea", "sb_accent": "#7046e8", "sb_on_accent": "#ffffff",
    "sb_lilac": "#e8deff", "sb_peach": "#ffe0cd", "sb_lime": "#dff6a5",
}

DARK = {
    "ink": "#e6f2f0",
    "slate": "#a9c4c0",
    "accent": "#2dd4bf",
    "on_accent": "#06201d",   # dark text on the mint accent keeps contrast above 7:1
    "line": "#223639",
    "mist": "#1b2f33",
    "bg": "#0a1214",
    "surface": "#101a1c",
    "good_bg": "#12352f", "good_text": "#7ee7d4",
    "gap_bg": "#3a1d1b", "gap_text": "#fca5a5",
    "kpi_bg": "#101a1c", "kpi_border": "1px solid #223639", "kpi_radius": "10px", "kpi_shadow": "none",
    "sb_bg": "#0c1517", "sb_card": "#101a1c", "sb_ink": "#e6f2f0", "sb_muted": "#a9c4c0",
    "sb_line": "#223639", "sb_accent": "#2dd4bf", "sb_on_accent": "#06201d",
    "sb_lilac": "#12302e", "sb_peach": "#3a2a1d", "sb_lime": "#25301a",   # teal / amber / olive tints
}

# Type scale (Heebo) — from Figma text styles
TYPE = {
    "title": (48, 800),      # page title "משרות"
    "job_title": (28, 800),  # detail card heading
    "kpi_value": (36, 800),  # KPI Card value
    "body": (15, 400),
    "label": (14, 400),      # KPI label, table text
    "chip": (13.5, 500),
    "button": (14, 600),
    "caption": (12.5, 400),
}

# Score → verdict thresholds (shared with job-matching)
STRONG, GOOD, STRETCH = 75, 60, 40


def css_vars(tokens: dict) -> str:
    return ":root{" + "".join(f"--jh-{k.replace('_', '-')}:{v};" for k, v in tokens.items()) + "}"
