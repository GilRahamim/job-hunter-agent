---
name: job-dashboard
description: The Streamlit dashboard for the Job Hunter project — Hebrew RTL layout, the jobs table with inline status editing, job detail panel, application pipeline, skill-gap insights, source health, profile view, and the "run now" button. Use this whenever working on dashboard.py or anything the owner sees in the browser, including charts, filters, styling, or performance of the UI.
---

# Dashboard (Streamlit)

One file, `dashboard.py` (split into `ui/` modules only if it passes ~500 lines). It reads from SQLite and writes only `status`/`notes`. Requires Streamlit ≥ 1.40 (row selection, `st.fragment`).

Load the `frontend-design` skill for visual polish once the functionality works.

## Page setup and RTL
```python
st.set_page_config(page_title="Job Hunter", page_icon="🎯", layout="wide")
st.markdown("""<style>
  .stApp, .stMarkdown, .stSelectbox label, .stMultiSelect label, .stSlider label,
  .stTextInput label, .stTabs [data-baseweb="tab"] { direction: rtl; text-align: right; }
  [data-testid="stSidebar"] { direction: rtl; }
  [data-testid="stDataFrame"], [data-testid="stDataEditor"], code, .ltr { direction: ltr; text-align: left; }
</style>""", unsafe_allow_html=True)
```
Tables stay LTR because job titles, companies and URLs are mostly English; Hebrew UI text is RTL. Wrap English-only fragments in `<span class="ltr">` when they appear inside Hebrew sentences.

## Data loading
```python
@st.cache_data(ttl=30)
def load_jobs() -> pd.DataFrame: ...   # db.all_jobs() → DataFrame, parse JSON lists, convert times to Asia/Jerusalem
```
Call `load_jobs.clear()` after any write so the UI reflects it immediately.

Derived columns: `age_days` (from `date_posted` or `first_seen`), `is_new` (first_seen within 24h), `stale` (last_seen older than 14 days → "ייתכן שנסגרה").

## Sidebar
- **הרץ סוכן עכשיו** button → `subprocess.Popen([sys.executable, "run_agent.py"], cwd=ROOT, stdout=log_file, stderr=STDOUT)`; store the PID in `st.session_state`; respect `data/run.lock`. A `@st.fragment(run_every=3)` shows the last ~15 log lines and a spinner until the process exits, then clears the cache.
- Last run: time (Israel), duration, new jobs, failed sources count.
- Filters: min score slider (default 60), sources multiselect, status multiselect (default all except `not_relevant`), location type (ישראל / מרחוק / הכול), posted within N days, free-text search over title/company/description, "רק חדשות" toggle.

## Tabs
1. **משרות** — KPI row (`st.metric`): total matching filters, new today, strong matches (≥75), applied. Then `st.data_editor` with:
   - `score` → `ProgressColumn(min_value=0, max_value=100, format="%d")`
   - `url` → `LinkColumn(display_text="פתח")`
   - `status` → `SelectboxColumn(options=STATUSES)` — the only editable column besides `notes`
   - columns: score, title, company, location, source, age_days, verdict, status, url
   - `disabled=[all other columns]`, `hide_index=True`, sorted by score desc
   After editing, diff against the original frame and call `db.update_status` for changed rows; show `st.toast("נשמר")`.
   Below the table: a selector (or row selection) opens the **detail panel**: title/company/location, score + verdict badge, `reasons`, `seniority_fit`, matching skills as green chips, missing skills as red chips, `cv_tip` in an `st.info`, notes `text_area` with save button, apply link button, and an expander with the full description. Plus the **"התאם קו"ח למשרה"** button (runs the tailoring agent in a subprocess, see `cv-tailoring`) and, when a tailored version exists, coverage before → after, download buttons for the DOCX/cover letter, and `changes.md` / `gaps.md` in expanders.
2. **תהליך** — count per status as a horizontal funnel (`new → interested → applied → interview → offer`), and a small table of jobs in `applied`/`interview` with days since `status_updated` (follow-up reminder when > 10 days).
3. **תובנות** — score histogram; jobs per source (and average score per source — tells which sources are worth keeping); **top missing skills among jobs scoring ≥ 60** (bar chart, top 15) — this is the owner's learning roadmap; top matching skills; new jobs per day over time.
4. **מקורות** — health of the last run per source (fetched, error, duration) with ✅/⚠️; history of fetched counts per source over the last 14 runs.
5. **פרופיל** — the extracted `CandidateProfile` (headline, seniority, years, skills as chips, target roles), CV file name and date; a note that editing `config.yaml → profile.overrides` corrects it.

## Charts
Use `st.bar_chart` / `st.line_chart` for simple ones; Plotly (`st.plotly_chart`) only where you need horizontal bars with long labels (skills). Load the `dataviz` skill if available before styling charts. Keep one accent color for "good" and one for "gap".

## Empty and error states
- No DB yet → a friendly Hebrew message: put the CV in `cv/`, then click "הרץ סוכן עכשיו".
- No jobs after filters → suggest lowering the score slider.
- Never crash the page on a malformed row; coerce with defaults.

## Performance
Hundreds to a few thousand rows is fine. Don't load `description` into the table frame (heavy) — fetch it for the selected job only.
