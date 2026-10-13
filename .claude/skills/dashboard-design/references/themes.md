# Themes

| Theme | Figma | Status | Where |
|---|---|---|---|
| **Sea** (light) | `2:30` + variables | implemented, render verified | `[theme.light]`, `tokens.LIGHT` |
| **Night** (dark) | `8:27` | implemented, render verified | `[theme.dark]`, `tokens.DARK` |
| **Paper** (light alt) | `8:665` | tokens only, **not rendered** | below |

Streamlit has exactly two theme slots (light, dark). A third theme therefore replaces one of them; it cannot sit beside them.

## Paper — how to switch to it (only if the owner asks)

1. Read `8:665` with `get_design_context` (load `figma-design-to-code` first) to confirm the values below, which were read from `8:678` and sampled from the screenshot.
2. In `config.toml`, replace `[theme.light]`/`[theme.light.sidebar]` with the Paper values; keep `[theme.dark]` as Night.
3. Fonts — Streamlit takes one body `font` and one `headingFont`:
   `font = "Assistant:https://fonts.googleapis.com/css2?family=Assistant:wght@400;600;700&display=swap"`
   `headingFont = "Frank Ruhl Libre:https://fonts.googleapis.com/css2?family=Frank+Ruhl+Libre:wght@500;700&display=swap"`
   The KPI value and score box use the heading face via CSS (`font-family: var(--jh-display)`).
4. Add a `PAPER` dict to `tokens.py` and use it for `light` in `inject_theme()`.
5. KPI cards become columns separated by a 1px rule on the right (`border-right: 1px solid #d2cbc0`, no background, no radius); value 52px Frank Ruhl Libre Bold.
6. Render, compare with `references/screens/figma-8-665-muted-editorial.png`, and iterate.

Paper tokens:

```python
PAPER = {
    "ink": "#302d28", "slate": "#5c574e", "accent": "#0f766e", "line": "#d2cbc0",
    "mist": "#e6dfd3", "bg": "#f5f1e8", "surface": "#fbf9f4",
    "good_bg": "transparent", "good_text": "#302d28",   # editorial chips are plain bold text
    "gap_bg": "transparent", "gap_text": "#302d28",
    "kpi_bg": "transparent", "kpi_border": "0", "kpi_radius": "0", "kpi_shadow": "none",
    "score_bg": "#302d28",
}
```
`slate` and `surface` are estimates (not read from Figma) — confirm them in step 1.
