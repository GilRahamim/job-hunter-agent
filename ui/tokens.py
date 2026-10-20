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
    "line": "#d9cfea",       # borders, rules — sidebar line (sb_line)
    "mist": "#e8deff",       # table header, tints — sidebar lilac (sb_lilac)
    "bg": "#f5f1ff",         # page — same as the sidebar (sb_bg)
    "surface": "#ffffff",    # color/surface      — cards, inputs
    "good_bg": "#d6efea", "good_text": "#0b5a53",   # color/chip-good-*
    "gap_bg": "#f6dad6", "gap_text": "#8e2f26",     # color/chip-gap-*
    "kpi_bg": "#ffffff", "kpi_border": "1px solid #d9cfea",   # white cards like the sidebar's
    "kpi_radius": "10px", "kpi_shadow": "none",
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
    "bg": "#0c1517",          # page — same as the sidebar (sb_bg)
    "surface": "#101a1c",
    "good_bg": "#12352f", "good_text": "#7ee7d4",
    "gap_bg": "#3a1d1b", "gap_text": "#fca5a5",
    "kpi_bg": "#101a1c", "kpi_border": "1px solid #223639", "kpi_radius": "10px", "kpi_shadow": "none",
    "sb_bg": "#0c1517", "sb_card": "#101a1c", "sb_ink": "#e6f2f0", "sb_muted": "#a9c4c0",
    "sb_line": "#223639", "sb_accent": "#2dd4bf", "sb_on_accent": "#06201d",
    "sb_lilac": "#12302e", "sb_peach": "#3a2a1d", "sb_lime": "#25301a",   # teal / amber / olive tints
}


def css_vars(tokens: dict) -> str:
    return ":root{" + "".join(f"--jh-{k.replace('_', '-')}:{v};" for k, v in tokens.items()) + "}"
