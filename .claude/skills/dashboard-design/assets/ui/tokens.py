"""Design tokens from Figma file xqkcOg1yGvJWFKwS14sEqf (Job Hunter Dashboard).

Single source of truth for anything .streamlit/config.toml cannot express.
Keep the two in sync: config.toml colors == these values.

LIGHT = "Sea"   — frame 2:30 "Dashboard / Jobs", Figma variables color/*
DARK  = "Night" — frame 8:27 "Variation 1 / Dark Moody Split"
"""

LIGHT = {
    "ink": "#16232b",        # color/ink          — primary text
    "slate": "#51636b",      # color/slate        — secondary text, labels
    "accent": "#0f766e",     # color/sea          — primary actions, score, active tab
    "line": "#d5dedb",       # color/line         — borders, rules
    "mist": "#e6ecea",       # color/mist         — KPI cards, sidebar, table header
    "bg": "#f4f6f5",         # color/bg           — page
    "surface": "#ffffff",    # color/surface      — cards, inputs
    "good_bg": "#d6efea", "good_text": "#0b5a53",   # color/chip-good-*
    "gap_bg": "#f6dad6", "gap_text": "#8e2f26",     # color/chip-gap-*
    "kpi_bg": "#e6ecea", "kpi_border": "0", "kpi_radius": "10px", "kpi_shadow": "none",
}

DARK = {
    "ink": "#f8fafc",
    "slate": "#cbd5e1",
    "accent": "#7c3aed",
    "line": "#2a2f36",
    "mist": "#27303c",
    "bg": "#0b0f14",
    "surface": "#11161d",
    "good_bg": "#0f172a", "good_text": "#93c5fd",
    "gap_bg": "#2a1414", "gap_text": "#fca5a5",
    "kpi_bg": "#11161d", "kpi_border": "1px solid #2a2f36", "kpi_radius": "16px",
    "kpi_shadow": "0 10px 12px rgba(0,0,0,.4)",
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
