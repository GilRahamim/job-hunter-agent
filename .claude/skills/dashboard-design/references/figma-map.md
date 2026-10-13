# Figma map — Job Hunter Dashboard

File: `https://www.figma.com/design/xqkcOg1yGvJWFKwS14sEqf/Job-Hunter-Dashboard`
**fileKey:** `xqkcOg1yGvJWFKwS14sEqf` · page `0:1` ("Page 1")

Node ids below were read on 2026-10-13. If a call returns "node not found", the frame was moved or rebuilt: run `get_metadata(fileKey, nodeId="0:1")` (the page is large, ~125k chars; filter the XML for `<frame` at depth 1) and update this file.

## Source of truth

| Node | Name | Role |
|---|---|---|
| `2:30` | Dashboard / Jobs (1500×1459) | **Primary design.** Light "Sea" theme. Everything is built from this unless the owner says otherwise. |
| `3:2` | └ Main (1200 wide) | Title, tabs, KPI row, jobs table, detail card |
| `3:280` | └ Sidebar (300 wide, on the right) | Brand, run button, last-run summary, filters |
| `2:16` | Components | Chip/Good `2:17`, Chip/Gap `2:19`, Chip/Plain `2:21`, KPI Card `2:23`, Button/Primary `2:26`, Button/Secondary `2:28` |

Figma variables (bound on `2:30`, read with `get_variable_defs`):
`color/ink #16232b` · `color/slate #51636b` · `color/sea #0f766e` · `color/line #d5dedb` · `color/mist #e6ecea` · `color/bg #f4f6f5` · `color/surface #ffffff` · `color/chip-good-bg #d6efea` · `color/chip-good-text #0b5a53` · `color/chip-gap-bg #f6dad6` · `color/chip-gap-text #8e2f26`

Type: **Heebo** — 400 (body/labels 14), 500 (chips 13.5), 600 (buttons 14), 800 (KPI value 36, page title ~48, job title ~28).
Radii: KPI card 10 · buttons 8 · chips 999 · detail card 12. Button padding 9×18. Chip padding 3×11. KPI padding 12×16.

## Full-page variations

| Node | Name | Use |
|---|---|---|
| `8:27` | Variation 1 / Dark Moody Split (1804×1178) | **Dark theme ("Night").** Palette is hard-coded (no variables): page `#0b0f14`, cards `#11161d`, border `#2a2f36`, table header `#27303c`, label text `#cbd5e1`, accent violet `#7c3aed`, KPI radius 16 + shadow `0 10 12 rgba(0,0,0,.4)`. Layout idea worth keeping: `8:45` "Split workspace" = table and detail panel side by side. |
| `8:665` | Variation 3 / Muted Minimal Editorial (1420×1831) | Alternative light theme ("Paper"). Page `#f5f1e8`, ink `#302d28`, rules `#d2cbc0`, table header `#e6dfd3`, accent `#0f766e`, score box `#302d28`. Fonts **Frank Ruhl Libre** Bold (title, KPI values 52, job title) + **Assistant** (body 16). KPI cards are rule-separated columns, not boxes. Not implemented — see `themes.md`. |

## Sidebar / filter-panel explorations

Six alternative treatments of the filter panel. None replaces `3:280` unless the owner picks one; fetch with `get_design_context` when asked.

| Node | Name | Idea |
|---|---|---|
| `7:2670` | Warm full-width filter bar (1440×439) | Filters as a horizontal bar above the content instead of a sidebar |
| `7:2590` | Cobalt split search workspace (1040×760) | Grouped controls in a wide two-column panel |
| `7:2657` | Display identity and agent (380×760) | Brand + agent launch as a separate column |
| `7:2506` | Editorial search panel (410×1313) | Serif masthead, rule-separated filter sections |
| `7:2424` | Playful career toolkit (728×942) | Asymmetric grid of filter cards |
| `7:2345` | Tactical search console (420×1053) | Dense "console" grouping: precision / recency / freshness zones |

## Not in Figma yet

Tabs **תהליך** (pipeline), **תובנות** (insights), **מקורות** (sources), **פרופיל** (profile) and the tailored-CV panel have no frames. Build them from the system (see SKILL.md → "Screens without a Figma frame"), and if the owner wants, push them back into Figma (see SKILL.md → "Round-trip").
