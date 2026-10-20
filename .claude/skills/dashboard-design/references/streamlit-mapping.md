# Figma → Streamlit mapping

Verified by rendering on **Streamlit 1.65** (2026-10-13) and comparing with frame `2:30`. Requires Streamlit ≥ 1.50 for `st.badge`, `st.space`, horizontal containers, `height="content"` and `row_height`; `requirements.txt` should pin `streamlit>=1.50`.

Contents: 1 the three layers · 2 tokens → config keys · 3 components · 4 DOM hooks · 5 pitfalls (all found the hard way)

## 1. Three layers, in this order of preference

1. **`.streamlit/config.toml` theme** — colors, fonts, radii, chart palettes, dataframe header. Native, so every widget follows it, including ones you don't style by hand. `[theme.light]` = Sea, `[theme.dark]` = Night; Streamlit follows the OS and the user can switch in the ⋮ menu.
2. **`ui/tokens.py` + `ui/theme.css`** — only what the theme can't express: RTL, title sizes, KPI card shape, score box, chip shape, white inputs in the main area. `inject_theme()` picks LIGHT/DARK from `st.context.theme.type`, so it follows the user's in-app choice, not just the OS.
3. **`ui/components.py`** — small functions that compose native widgets (`kpi_row`, `chips`, `score_box`, `title`, `section_label`). Pages call these; pages never contain raw CSS or hex colors.

## 2. Tokens → config keys (light)

| Figma | config.toml `[theme.light]` | Note |
|---|---|---|
| `color/sea` | `primaryColor` | buttons, tabs, sliders, ProgressColumn bars, pills |
| `color/ink` | `textColor` | |
| `color/mist` | `secondaryBackgroundColor`, `dataframeHeaderBackgroundColor`, `[theme.light.sidebar] backgroundColor` | |
| `color/line` | `borderColor`, `dataframeBorderColor` | |
| `color/slate` | `dataframeHeaderTextColor`, `grayTextColor` | |
| `color/surface` | `backgroundColor` (**not** `color/bg`) | the data grid paints its rows with `backgroundColor`; Figma rows are white |
| `color/bg` | `.stApp` background in `theme.css` | page gray painted by CSS because of the row above |
| `color/chip-good-*` | `greenBackgroundColor` / `greenTextColor` | `st.badge(color="green")` |
| `color/chip-gap-*` | `redBackgroundColor` / `redTextColor` | `st.badge(color="red")` |
| tip box teal tint | `blueBackgroundColor` / `blueTextColor` | `st.info` is the tip box; blue is remapped to sea |
| Heebo | `font = "Heebo:<google fonts css url>"`, `headingFont = "Heebo"` | |
| radii 10 / 8 | `baseRadius = "10px"`, `buttonRadius = "8px"` | |
| KPI value 36 / 800 | `metricValueFontSize`, `metricValueFontWeight` | |

Dark uses the same keys under `[theme.dark]` with the Night palette (`figma-map.md`).

## 3. Components

| Figma | Streamlit | How |
|---|---|---|
| Button/Primary `2:26` | `st.button(label, type="primary")` | color from `primaryColor`, radius from `buttonRadius` |
| Button/Secondary `2:28` | `st.button(label)` / `st.link_button(label, url)` | |
| KPI Card `2:23` | `components.kpi_row([...])` → `st.metric` inside `st.container(key="kpis", horizontal=True)` | card shape from `.st-key-kpis [data-testid="stMetric"]` |
| Chip/Good, Chip/Gap, Chip/Plain | `components.chips(skills, "good" \| "gap" \| "plain")` → `st.badge` | pill shape from `.stMarkdownBadge` |
| Tabs | `st.tabs([...])` | underline style in CSS |
| Jobs table | `st.dataframe(..., height="content", row_height=44)` + `column_config.ProgressColumn` for score, `LinkColumn(display_text="פתח")` | use `st.data_editor` with `SelectboxColumn` when status is editable |
| Score box (100) | `components.score_box(score)` | the only raw HTML element on the page |
| Tip | `st.info(text)` | |
| Status filter chips | `st.pills(..., selection_mode="multi")` | |
| Location radio | `st.radio(..., horizontal=True)` | |
| Toggle | `st.toggle` | |
| Detail card | `st.container(key="detail-card")` | card style from `.st-key-detail-card` |

## 4. DOM hooks (stable ones only)

Use, in this order: **`.st-key-<key>`** (Streamlit adds it to any keyed container/widget — the most stable hook), **`[data-testid="…"]`**, `[data-baseweb="…"]`. Never target `st-emotion-cache-*` classes: they change between releases.

Verified test ids: `stApp`, `stAppViewContainer`, `stSidebar`, `stMain`, `stHeader`, `stMetric`, `stMetricLabel`, `stMetricValue`, `stTabs`, `stDataFrame`, `stTextAreaRootElement`, `stTextInputRootElement`, `stAlertContainer`, `stMarkdownContainer`, `stCaptionContainer`. Badge span class: `stMarkdownBadge`.

## 5. Pitfalls

- **Sidebar side.** `direction: rtl` on `.stApp` already puts the sidebar on the right. Adding `flex-direction: row-reverse` flips it back to the left.
- **Sidebar open/collapsed attribute changed in 1.66.** Up to 1.65 `stSidebar` carries `aria-expanded="true|false"`; from 1.66 it is `data-collapsed="false|true"` (and an inline `width: 281.25px`). A rule on only one of them silently stops matching after a `pip install` upgrade: the sidebar falls back to ~281px and its text is clipped. `ui/theme.css` selects both.
- **Table rows can't be styled with CSS.** The grid is a canvas: row/cell colors come only from the theme (`backgroundColor`, `dataframeHeader*`, `dataframeBorderColor`). Hence `backgroundColor = surface` and the page color via CSS.
- **RTL in the grid.** The canvas stays left-to-right. Get the Figma order (score on the right) by listing `column_order` in reverse. Don't set `direction: rtl` on the grid.
- **Empty last row.** A fixed `height` leaves a blank row; `height="content"` fits exactly.
- **Theme changes need a server restart.** `config.toml` is read at startup; CSS/Python changes hot-reload, theme colors don't.
- **Inputs in the main area turn gray.** They use `secondaryBackgroundColor`; Figma has them white → `[data-testid="stMain"] [data-testid="stTextAreaRootElement"]` in CSS.
- **Dark detection.** Use `st.context.theme.type`, not `@media (prefers-color-scheme)`: the user can choose dark in the ⋮ menu while the OS is light.
- **`st.html` for styles.** `st.html("<style>…</style>")` injects CSS without leaving a visible block; keep all CSS in `theme.css`.
- **Deploy button.** `[client] toolbarMode = "minimal"` removes it.
