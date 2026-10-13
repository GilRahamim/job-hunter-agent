---
name: dashboard-design
description: Visual design system for the Job Hunter Streamlit dashboard, sourced from the owner's Figma file through the Figma MCP — verified theme config (light "Sea" / dark "Night"), design tokens, RTL Hebrew CSS, component helpers, Figma node map, and a render-and-compare loop against Figma screenshots. Use this whenever the dashboard's look is involved — styling dashboard.py, colors, fonts, spacing, the table, KPI cards, chips, dark mode, a new tab or screen, matching or syncing with Figma, or any figma.com link for this project — even if the request only says "make it look better" or "fix the layout".
---

# Dashboard design (Figma → Streamlit)

The owner designed the dashboard in Figma. This skill turns that design into Streamlit faithfully and keeps the two in sync. It covers **how it looks**; what the dashboard does (tabs, filters, status editing, run button) is in the `job-dashboard` skill — load both when building a screen.

Everything in `assets/` was rendered on Streamlit 1.65 and compared with the Figma frame side by side before this skill was written (`references/screens/verified-render-*.png` vs `figma-*.png`). Start from those assets rather than re-deriving them; the pitfalls they avoid are listed in `references/streamlit-mapping.md` §5.

## Figma file

- URL: `https://www.figma.com/design/xqkcOg1yGvJWFKwS14sEqf/Job-Hunter-Dashboard` · fileKey `xqkcOg1yGvJWFKwS14sEqf`
- **Primary design: `2:30` "Dashboard / Jobs"** (light, Figma variables). Components: `2:16`.
- Dark theme: `8:27` "Dark Moody Split". Alternative light theme: `8:665` "Muted Minimal Editorial". Six sidebar explorations.
- Full node map, palettes and type scale: **`references/figma-map.md`**.

## Figma MCP rules

The Figma MCP must be connected in Claude Code (check with `/mcp`). If it isn't, the PNGs in `references/screens/` are the fallback visual target — say that you're working from them.

- Load the **`figma-design-to-code`** skill before any `get_design_context` call (the server requires it), and pass `skillNames: "figma-design-to-code"`.
- Cheap → expensive: `get_variable_defs` (tokens) → `get_screenshot` (visual target) → `get_design_context` on the **smallest node** that answers the question. Calling `get_metadata` on page `0:1` returns ~125k characters; filter it, don't read it whole.
- `get_design_context` returns React + Tailwind. It is a **spec**, not code to paste: translate to config.toml keys, tokens and Streamlit widgets using `references/streamlit-mapping.md`. Never add Tailwind or React.
- A screenshot is the visual target only — never embed it in the app. Figma asset URLs expire after ~7 days; nothing in the repo may point to them.
- Variations (`8:27`, `8:665`) hard-code colors instead of variables: read values from `get_design_context` on a small node (e.g. a KPI card), not by guessing from pixels.

## Architecture — three layers

```
.streamlit/config.toml   theme: colors, fonts, radii, chart palettes   (native, preferred)
ui/tokens.py             LIGHT / DARK dicts + type scale — mirror of config.toml
ui/theme.css             only what the theme can't do: RTL, card shapes, score box, chip shape
ui/components.py         inject_theme(), title(), kpi_row(), chips(), score_box(), section_label()
dashboard.py             pages compose components; no hex colors, no raw CSS here
```

Rule of thumb: if a value can live in `config.toml`, it lives there. CSS only for what Streamlit can't express, hooked on `.st-key-<key>` or `[data-testid]`, never on `st-emotion-cache-*` classes.

## Workflow A — first-time setup (dashboard not styled yet)

1. Copy into the project root:
   - `assets/.streamlit/config.toml` → `.streamlit/config.toml`
   - `assets/ui/` → `ui/`
2. `requirements.txt`: `streamlit>=1.50`; dev only: `playwright`, `pillow`.
3. In `dashboard.py`, right after `st.set_page_config(page_title="Job Hunter", page_icon="🎯", layout="wide")`, call `inject_theme()`. Build the Jobs tab following **`assets/reference_app.py`**. It reproduces frame `2:30` with static data: copy its structure and swap in real data from `db.py` — column order, `row_height=44`, `height="content"`, the detail card and the sidebar order are all deliberate.
4. Restart Streamlit (theme changes need a restart), then run the compare loop (below) in both schemes.

## Workflow B — the owner changed Figma

1. `get_variable_defs(fileKey, "2:30")` → diff against `tokens.LIGHT`, and update `tokens.py` **and** `config.toml` together (they must stay equal).
2. For a layout change: `get_screenshot` of the changed frame → `get_design_context` on the changed node only → apply it with the mapping.
3. If a new frame appeared, add it to `references/figma-map.md`.
4. Compare loop.

## Workflow C — screens without a Figma frame

Pipeline, Insights, Sources, Profile and the tailored-CV panel have no frames. Build them from the system so they look like siblings of `2:30`:

- **Page skeleton** (every tab): `title()` → `st.tabs` → a KPI row when there are numbers worth glancing at → the main element → details. Content width = main column; gaps 16px between cards, 24–32px between sections (`st.space("small"|"medium")`).
- **Pipeline (תהליך):** a KPI row of counts per status, in funnel order (חדש → מעניין → הוגש → ראיון → הצעה). Below it, a horizontal bar chart (`st.bar_chart(horizontal=True)` or Plotly). Bars use `primaryColor`; rejected/not-relevant are gray. Then a table of applied/interview jobs with "days since update", with a red badge when over 10.
- **Insights (תובנות):**
  - Score histogram, bars in the primary color.
  - "Most-missed skills" chart: horizontal bars in the **gap** color (`#8e2f26` light / `#fca5a5` dark), because they are gaps.
  - Top matching skills in the **good** color.
  - Jobs per source as a table with an average-score ProgressColumn.
  - Load the `dataviz` skill if available; chart palettes are already set in config (`chartCategoricalColors` / `chartSequentialColors`).
- **Sources (מקורות):** a table with one row per source. Status is a badge: green "תקין", red "שגיאה" with the error as `help` text. Next to it, the last 14 runs as a small line chart.
- **Profile (פרופיל):** the headline as `jh-job-title` style, then skills via `chips(..., "plain")` grouped by category, target roles as plain chips, and the CV file name and date in caption style.
- **Tailored-CV panel** (inside the detail card): coverage before → after as two `st.metric` with a delta, download buttons as secondary buttons, and `changes.md` / `gaps.md` in `st.expander`.
- **Dark "split workspace"** (from `8:27`): on screens ≥ 1400px the owner may prefer table and detail side by side — `st.columns([7, 4])`, detail on the left (RTL: the table stays on the right). Offer it; don't switch silently.

When a new screen looks right, offer to push it to Figma (see Round-trip) so the file stays the source of truth.

## Design rules (apply everywhere)

- **Color has meaning.** Primary (sea/violet) = the one main action per area, the score, and the selected state. Green chips = skills you have. Red = gaps, failures, overdue — nothing decorative is red. Everything else is ink/slate on surface/mist.
- **One primary button per area.** "מצא משרה חדשה" in the sidebar, "שמור הערות" in the detail card; everything else is secondary.
- **RTL with LTR islands.** Hebrew UI flows right-to-left. Job titles, companies, locations, skills, URLs and numbers stay LTR (`.ltr`, or the grid, which is LTR). In the table, the first column on the right is **ציון** — achieved by reversing `column_order`.
- **Type:** Heebo only (Sea/Night). 48/800 page title, 28/800 job title, 36/800 KPI value, 15 body, 14 labels, 13.5/500 chips, 12.5 captions. Don't introduce new sizes — pick the nearest.
- **Density:** table rows 44px; cards 12–16px inner padding (KPI) and 28px (detail card); sidebar widgets keep Streamlit's default spacing.
- **Empty and error states** use the same vocabulary: `st.info` (sea tint) for guidance, `st.warning` only for something the owner must act on, `st.error` for failures. One short Hebrew sentence plus the next action.
- **Both schemes, always.** Every visual change is checked in light *and* dark. New CSS uses `var(--jh-*)` tokens, never hex.

## Compare loop (verification)

With `streamlit run dashboard.py` running:

```bash
python .claude/skills/dashboard-design/scripts/compare.py            # light + dark vs Figma 2:30 / 8:27
python .claude/skills/dashboard-design/scripts/compare.py --scheme light \
    --figma .claude/skills/dashboard-design/references/screens/figma-2-30-dashboard-jobs.png
```

Output goes to `data/design-check/compare-<scheme>.png` (app on the left, Figma on the right). **Open the image and look at it** before saying a screen is done. Check, in this order:
1. Layout: sidebar on the right, section order, alignment.
2. Colors: page, cards, table header, primary, chips.
3. Type: sizes and weights of the title, KPI values and job title.
4. Spacing.
5. Both schemes.

List the differences you see and fix them, or explain why one is a Streamlit limit (e.g. sidebar width is ~280px, not 300). For a fresh Figma target, `get_screenshot` the frame, download it with the `curl` command the tool prints, and pass it as `--figma`.

First run: `pip install playwright pillow && python -m playwright install chromium`.

## Round-trip (code → Figma), when the owner asks

For a screen built in code that should exist in Figma: load the Figma plugin's `figma-generate-design` skill (and `figma-use` before any `use_figma` call), reuse the components in `2:16` and the `color/*` variables rather than raw values, and place the new frame next to `2:30`. Then add its node id to `references/figma-map.md`.

## Files in this skill

- `assets/.streamlit/config.toml` — verified light + dark theme
- `assets/ui/tokens.py`, `theme.css`, `components.py` — the design layer
- `assets/reference_app.py` — frame `2:30` rebuilt with static data
- `scripts/compare.py` — render + side-by-side with Figma
- `references/figma-map.md` — node ids, palettes, type scale
- `references/streamlit-mapping.md` — token → config key, component mapping, DOM hooks, pitfalls
- `references/themes.md` — Sea / Night / Paper, and how to switch to Paper
- `references/screens/` — Figma frames and verified renders (offline visual targets)
