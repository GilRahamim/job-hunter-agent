"""Streamlit dashboard: browse scored jobs, track applications. Hebrew UI, RTL.

Reads from SQLite; writes only `status` and `notes`."""
from __future__ import annotations

import html
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from jobhunter import db
from jobhunter.config import ROOT

IL = ZoneInfo("Asia/Jerusalem")
LOG_PATH = ROOT / "data" / "logs" / "dashboard-run.log"
LOCK_PATH = ROOT / "data" / "run.lock"

# design tokens: sea-green = good, coral = gap, slate = text
INK, SEA, CORAL, MIST, AMBER = "#16232B", "#0F766E", "#C2453A", "#E6ECEA", "#B7791F"

STATUS_HE = {"new": "חדש", "interested": "מעניין", "applied": "הוגשה מועמדות", "interview": "ראיון",
             "offer": "הצעה", "rejected": "נדחה", "not_relevant": "לא רלוונטי"}
HE_STATUS = {v: k for k, v in STATUS_HE.items()}
FUNNEL = ["new", "interested", "applied", "interview", "offer"]
VERDICT_HE = {"strong": "חזקה", "good": "טובה", "stretch": "מתיחה", "poor": "חלשה"}

st.set_page_config(page_title="Job Hunter", page_icon=":material/work_history:", layout="wide")

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700;800&display=swap');
html, body, .stApp, [class*="st-"], button, input, textarea {{ font-family: 'Heebo', sans-serif; }}
[data-testid="stIconMaterial"], .material-icons, [class*="material-symbols"] {{ font-family: 'Material Symbols Rounded', 'Material Icons' !important; }}
.stApp, .stMarkdown, label, .stTabs [data-baseweb="tab"], [data-testid="stSidebar"],
[data-testid="stMetric"], .stAlert, .stButton, .stToggle {{ direction: rtl; text-align: right; }}
[data-testid="stDataFrame"], [data-testid="stDataEditor"], code, .ltr, .js-plotly-plot {{ direction: ltr; text-align: left; }}
h1, h2, h3 {{ font-weight: 800; letter-spacing: -0.01em; color: {INK}; }}
[data-testid="stMetricValue"] {{ font-weight: 800; font-feature-settings: 'tnum'; }}
[data-testid="stMetric"] {{ background: {MIST}; border-radius: 10px; padding: .7rem 1rem; }}
.chip {{ display:inline-block; padding:.12rem .65rem; margin:.15rem .1rem; border-radius:999px;
  font-size:.85rem; font-weight:500; direction:ltr; }}
.chip-good {{ background:#D6EFEA; color:#0B5A53; }}
.chip-gap {{ background:#F6DAD6; color:#8E2F26; }}
.chip-plain {{ background:{MIST}; color:{INK}; }}
.score-badge {{ display:inline-block; min-width:4.2rem; text-align:center; font-weight:800; font-size:2.4rem;
  line-height:1; padding:.5rem .8rem; border-radius:12px; color:#fff; direction:ltr; }}
.job-title {{ font-size:1.5rem; font-weight:800; margin:0; direction:ltr; text-align:left; }}
.job-meta {{ color:#51636B; direction:ltr; text-align:left; margin:.1rem 0 .6rem; }}
button, [role="tab"], [role="radio"], [data-baseweb="select"], label {{ cursor: pointer; }}
button, [role="tab"], a {{ transition: background-color .15s ease, color .15s ease, border-color .15s ease; }}
:focus-visible {{ outline: 3px solid {SEA}; outline-offset: 2px; border-radius: 6px; }}
.stButton > button, .stDownloadButton > button, [data-testid="stLinkButton"] a {{ min-height: 44px; }}
.block-container {{ padding-top: 2.2rem; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
@media (max-width: 640px) {{ .score-badge {{ font-size: 1.8rem; }} .job-title {{ font-size: 1.2rem; }} }}
.empty {{ padding:2rem; border:1px dashed #9AAAA6; border-radius:12px; text-align:center; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------ data

def to_il(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(IL)


@st.cache_data(ttl=30)
def load_jobs() -> pd.DataFrame:
    rows = db.jobs_table()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    now = datetime.now(IL)
    first = df["first_seen"].map(to_il)
    last = df["last_seen"].map(to_il)
    posted = pd.to_datetime(df["date_posted"], errors="coerce")
    base = posted.fillna(pd.to_datetime(first.map(lambda d: d.date() if d else None)))
    df["age_days"] = ((pd.Timestamp(now.date()) - base).dt.days).clip(lower=0)
    df["is_new"] = first.map(lambda d: bool(d) and now - d < timedelta(hours=24))
    df["stale"] = last.map(lambda d: bool(d) and now - d > timedelta(days=14))
    df["first_seen_il"] = first
    df["where"] = df.apply(lambda r: r["location"] or r["remote_region"] or ("Remote" if r["is_remote"] else ""), axis=1)
    df["score"] = df["score"].fillna(0).astype(float)
    df["notes"] = df["notes"].fillna("")
    for col in ("matching_skills", "missing_skills"):
        df[col] = df[col].map(lambda v: v if isinstance(v, list) else [])
    return df.set_index("id", drop=False)


def refresh() -> None:
    load_jobs.clear()
    st.rerun()


def chips(items: list[str], kind: str) -> str:
    return "".join(f'<span class="chip chip-{kind}">{html.escape(i)}</span>' for i in items) or "—"


def score_color(score: float) -> str:
    return SEA if score >= 75 else AMBER if score >= 60 else "#6B7C85"


def is_running() -> int | None:
    from jobhunter.agent import pid_alive
    try:
        pid = int(LOCK_PATH.read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) else None


# ------------------------------------------------------------ sidebar

def start_run() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log = open(LOG_PATH, "w", encoding="utf-8")
    subprocess.Popen([sys.executable, "run_agent.py"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    st.session_state["was_running"] = True


@st.fragment(run_every=3)
def run_panel() -> None:
    pid = is_running()
    if pid:
        st.session_state["was_running"] = True
        st.info("הסוכן רץ עכשיו…")
        if LOG_PATH.exists():
            st.code("\n".join(LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]),
                    language=None)
    elif st.session_state.pop("was_running", False):
        load_jobs.clear()
        st.rerun()
    else:
        if st.button("הרץ סוכן עכשיו", type="primary", width="stretch", icon=":material/play_arrow:"):
            start_run()
            st.rerun()


def sidebar(df: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown("### Job Hunter")
        run_panel()
        runs = db.last_runs(1)
        if runs:
            r, s = runs[0], runs[0]["stats"]
            when = to_il(r["finished"] or r["started"])
            failed = len(s.get("errors", []))
            st.caption(f"ריצה אחרונה: {when:%d/%m %H:%M} · {s.get('duration_s', '?')} שנ׳ · "
                       f"{s.get('kept', 0)} חדשות · {failed} מקורות עם תקלה")
        st.divider()
        if df.empty:
            return df
        min_score = st.slider("ציון מינימלי", 0, 100, 60)
        sources = st.multiselect("מקור", sorted(df["source"].unique()), default=[])
        statuses = st.multiselect("סטטוס", list(STATUS_HE.values()),
                                  default=[v for k, v in STATUS_HE.items() if k != "not_relevant"])
        loc = st.radio("מיקום", ["הכול", "ישראל", "מרחוק"], horizontal=True)
        days = st.slider("פורסמו ב-N הימים האחרונים", 1, 90, 60)
        query = st.text_input("חיפוש חופשי (כותרת / חברה)")
        only_new = st.toggle("רק חדשות (24 שעות)")

    out = df[df["score"] >= min_score]
    if sources:
        out = out[out["source"].isin(sources)]
    out = out[out["status"].map(STATUS_HE).isin(statuses)]
    if loc == "מרחוק":
        out = out[out["is_remote"] == 1]
    elif loc == "ישראל":
        out = out[out["is_remote"] != 1]
    out = out[out["age_days"].fillna(0) <= days]
    if query:
        q = query.lower()
        out = out[out["title"].str.lower().str.contains(q, na=False) | out["company"].str.lower().str.contains(q, na=False)]
    if only_new:
        out = out[out["is_new"]]
    return out


# ------------------------------------------------------------ tabs

def jobs_tab(df: pd.DataFrame, shown: pd.DataFrame) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("משרות מתאימות", len(shown))
    c2.metric("חדשות היום", int(shown["is_new"].sum()))
    c3.metric("התאמה חזקה (75+)", int((shown["score"] >= 75).sum()))
    c4.metric("הוגשה מועמדות", int((df["status"] == "applied").sum()))

    if shown.empty:
        st.markdown('<div class="empty">אין משרות שעונות על הסינון. נסו להוריד את הציון המינימלי.</div>',
                    unsafe_allow_html=True)
        return

    view = shown.sort_values("score", ascending=False).copy()
    view["verdict_he"] = [VERDICT_HE.get(v) or "ראשוני" for v in view["verdict"]]
    view["status_he"] = view["status"].map(STATUS_HE)
    view["title_flag"] = [("● " if n else "○ " if s else "") + t
                          for t, n, s in zip(view["title"], view["is_new"], view["stale"])]
    cols = ["score", "title_flag", "company", "where", "source", "age_days", "verdict_he", "status_he", "url"]
    table = view[cols]
    edited = st.data_editor(
        table, hide_index=True, width="stretch", height=min(560, 36 * (len(table) + 1) + 6), row_height=36, key="jobs_editor",
        disabled=[c for c in cols if c != "status_he"],
        column_config={
            "score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d"),
            "title_flag": st.column_config.TextColumn("תפקיד", width="large"),
            "company": "חברה", "where": "מיקום", "source": "מקור",
            "age_days": st.column_config.NumberColumn("ימים", format="%d"),
            "verdict_he": "הערכה",
            "status_he": st.column_config.SelectboxColumn("סטטוס", options=list(STATUS_HE.values()), required=True),
            "url": st.column_config.LinkColumn("קישור", display_text="פתח"),
        })
    changed = edited.index[edited["status_he"] != table["status_he"]]
    for job_id in changed:
        db.update_status(job_id, HE_STATUS[edited.loc[job_id, "status_he"]])
    if len(changed):
        st.toast("נשמר")
        refresh()
    st.caption("● = חדשה (24 שעות) · ○ = לא נראתה מעל שבועיים, ייתכן שנסגרה · ציון 'ראשוני' = הערכה אוטומטית ללא מודל שפה")
    detail_panel(view)


def detail_panel(view: pd.DataFrame) -> None:
    st.divider()
    ids = list(view.index)
    labels = {i: f"{view.loc[i, 'score']:.0f} · {view.loc[i, 'title']} — {view.loc[i, 'company']}" for i in ids}
    job_id = st.selectbox("פרטי משרה", ids, format_func=labels.get, label_visibility="collapsed")
    job = db.job_detail(job_id)
    if not job:
        return
    score = job["score"] or 0
    left, right = st.columns([1, 6])
    left.markdown(f'<div class="score-badge" style="background:{score_color(score)}">{score:.0f}</div>',
                  unsafe_allow_html=True)
    where = job["location"] or job["remote_region"] or ("Remote" if job["is_remote"] else "")
    right.markdown(f'<p class="job-title">{html.escape(job["title"])}</p>'
                   f'<p class="job-meta">{html.escape(job["company"])} · {html.escape(where)} · {html.escape(job["source"])}</p>',
                   unsafe_allow_html=True)
    if job["verdict"]:
        right.caption(f"הערכה: {VERDICT_HE.get(job['verdict'], job['verdict'])} · {job['scored_by']}")
    else:
        right.caption("ציון ראשוני (חישוב אוטומטי). הערכת מודל שפה תתווסף כשהמפתח יופעל.")
    if job["reasons"]:
        st.markdown(job["reasons"])
    if job["seniority_fit"]:
        st.markdown(f"**התאמת ותק:** {job['seniority_fit']}")
    a, b = st.columns(2)
    a.markdown("**כישורים תואמים**")
    a.markdown(chips(job["matching_skills"] or [], "good"), unsafe_allow_html=True)
    b.markdown("**כישורים חסרים**")
    b.markdown(chips(job["missing_skills"] or [], "gap"), unsafe_allow_html=True)
    if job["cv_tip"]:
        st.info(job["cv_tip"])
    notes = st.text_area("הערות", job["notes"] or "", key=f"notes_{job_id}")
    c1, c2 = st.columns([1, 5])
    if c1.button("שמור הערות", key=f"save_{job_id}"):
        db.update_notes(job_id, notes)
        st.toast("נשמר")
        load_jobs.clear()
    if job["url"]:
        c2.link_button("פתח את המשרה", job["url"])
    with st.expander("תיאור המשרה המלא"):
        st.text(job["description"] or "—")


def pipeline_tab(df: pd.DataFrame) -> None:
    counts = df["status"].value_counts()
    fig = go.Figure(go.Bar(y=[STATUS_HE[s] for s in FUNNEL][::-1], x=[int(counts.get(s, 0)) for s in FUNNEL][::-1],
                           orientation="h", marker_color=SEA, textposition="outside",
                           text=[int(counts.get(s, 0)) for s in FUNNEL][::-1]))
    fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=False, visible=False))
    st.plotly_chart(fig, width="stretch")
    active = df[df["status"].isin(["applied", "interview"])].copy()
    if active.empty:
        st.markdown('<div class="empty">עוד לא הוגשו מועמדויות. שנו סטטוס בטבלת המשרות כדי לעקוב כאן.</div>',
                    unsafe_allow_html=True)
        return
    now = datetime.now(IL)
    active["since"] = active["status_updated"].map(lambda t: (now - to_il(t)).days if to_il(t) else None)
    active["follow_up"] = active["since"].map(lambda d: "לחזור אליהם" if d is not None and d > 10 else "")
    active["status_he"] = active["status"].map(STATUS_HE)
    st.dataframe(active[["title", "company", "status_he", "since", "follow_up", "url"]], hide_index=True,
                 width="stretch",
                 column_config={"title": "תפקיד", "company": "חברה", "status_he": "סטטוס",
                                "since": "ימים מאז העדכון", "follow_up": "תזכורת",
                                "url": st.column_config.LinkColumn("קישור", display_text="פתח")})


def bar(labels: list[str], values: list[float], color: str, height: int = 420) -> go.Figure:
    fig = go.Figure(go.Bar(y=labels[::-1], x=values[::-1], orientation="h", marker_color=color,
                           text=values[::-1], textposition="outside"))
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                      xaxis=dict(showgrid=True, gridcolor=MIST))
    return fig


def insights_tab(df: pd.DataFrame) -> None:
    hist = go.Figure(go.Histogram(x=df["score"], xbins=dict(start=0, end=100, size=5), marker_color=SEA))
    hist.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                       xaxis_title="ציון", yaxis=dict(gridcolor=MIST), bargap=0.05)
    st.subheader("התפלגות ציונים")
    st.plotly_chart(hist, width="stretch")

    left, right = st.columns(2)
    per_src = df.groupby("source")["score"].agg(["count", "mean"]).sort_values("count", ascending=False)
    left.subheader("משרות וציון ממוצע לפי מקור")
    left.dataframe(per_src.rename(columns={"count": "משרות", "mean": "ציון ממוצע"}).round(1), width="stretch")
    per_day = df.dropna(subset=["first_seen_il"]).groupby(df["first_seen_il"].map(lambda d: d.date())).size()
    right.subheader("משרות חדשות ליום")
    right.bar_chart(per_day, color=SEA)

    good = df[df["score"] >= 60]
    miss = Counter(s for lst in good["missing_skills"] for s in lst).most_common(15)
    have = Counter(s for lst in good["matching_skills"] for s in lst).most_common(15)
    st.subheader("מפת דרכים ללמידה: הכישורים שחסרים הכי הרבה")
    if miss:
        st.plotly_chart(bar([m[0] for m in miss], [m[1] for m in miss], CORAL), width="stretch")
    else:
        st.markdown('<div class="empty">אין עדיין נתוני כישורים חסרים. הם מגיעים מהערכת מודל השפה, '
                    'ויופיעו אחרי ריצה עם מפתח API פעיל.</div>', unsafe_allow_html=True)
    if have:
        st.subheader("הכישורים שמתאימים הכי הרבה")
        st.plotly_chart(bar([h[0] for h in have], [h[1] for h in have], SEA), width="stretch")


def sources_tab() -> None:
    runs = db.last_runs(1)
    if not runs:
        st.markdown('<div class="empty">עוד לא הייתה ריצה.</div>', unsafe_allow_html=True)
        return
    health = pd.DataFrame(db.health_for_run(runs[0]["id"]))
    if health.empty:
        return
    health["מצב"] = health["error"].map(lambda e: f"תקלה: {e}" if e else "תקין")
    st.dataframe(health[["source", "fetched", "duration_s", "מצב"]].rename(
        columns={"source": "מקור", "fetched": "נשלפו", "duration_s": "שניות"}), hide_index=True, width="stretch")
    hist = pd.DataFrame(db.health_history(14))
    if not hist.empty and hist["run_id"].nunique() > 1:
        st.subheader("נשלפו לפי ריצה")
        st.line_chart(hist.pivot_table(index="run_id", columns="source", values="fetched"))


def profile_tab() -> None:
    latest = db.latest_profile()
    if not latest:
        st.markdown('<div class="empty">אין פרופיל עדיין. שימו את קורות החיים בתיקיית cv/ והריצו את הסוכן.</div>',
                    unsafe_allow_html=True)
        return
    p = latest["data"]
    heuristic = latest["cv_hash"].endswith(":heuristic")
    st.markdown(f"### {p.get('name') or '—'}")
    st.markdown(f"<span class='ltr'>{html.escape(p.get('headline', ''))}</span>", unsafe_allow_html=True)
    st.caption(f"קובץ: {latest['cv_file']} · ותק: {p.get('seniority')} · {p.get('years_experience')} שנות ניסיון"
               + (" · פרופיל ראשוני (ללא מודל שפה)" if heuristic else ""))
    st.markdown("**כישורים**")
    st.markdown(chips(p.get("skills", []), "plain"), unsafe_allow_html=True)
    st.markdown("**תפקידי יעד**")
    st.markdown(chips(p.get("target_roles", []), "good"), unsafe_allow_html=True)
    st.info("כדי לתקן את החילוץ בלי לערוך את קורות החיים: config.yaml ← profile.overrides")


# ------------------------------------------------------------ main

def main() -> None:
    df = load_jobs()
    shown = sidebar(df)
    st.title("משרות")
    if df.empty:
        st.markdown('<div class="empty">עוד אין משרות. שימו את קורות החיים בתיקיית cv/ ולחצו '
                    '"הרץ סוכן עכשיו".</div>', unsafe_allow_html=True)
        tabs = st.tabs(["מקורות", "פרופיל"])
        with tabs[0]:
            sources_tab()
        with tabs[1]:
            profile_tab()
        return
    t_jobs, t_flow, t_ins, t_src, t_prof = st.tabs(["משרות", "תהליך", "תובנות", "מקורות", "פרופיל"])
    with t_jobs:
        jobs_tab(df, shown)
    with t_flow:
        pipeline_tab(df)
    with t_ins:
        insights_tab(df)
    with t_src:
        sources_tab()
    with t_prof:
        profile_tab()


main()
