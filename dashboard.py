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
from jobhunter.config import ROOT, load_config
from ui.components import (brand_header, chips, inject_theme, kpi_row, question, score_box,
                           section_label, theme_toggle, title)
from ui.tokens import DARK, LIGHT

IL = ZoneInfo("Asia/Jerusalem")
LOG_PATH = ROOT / "data" / "logs" / "dashboard-run.log"
LOCK_PATH = ROOT / "data" / "run.lock"

_scheme = getattr(getattr(st.context, "theme", None), "type", None) or "light"
_T = DARK if _scheme == "dark" else LIGHT
# charts: accent = good, gap color = missing skills (same tokens as the Figma design)
INK, SEA, CORAL, MIST = _T["ink"], _T["accent"], _T["gap_text"], _T["mist"]

STATUS_HE = {"new": "חדש", "interested": "מעניין", "applied": "הוגשה מועמדות", "interview": "ראיון",
             "offer": "הצעה", "rejected": "נדחה", "not_relevant": "לא רלוונטי"}
HE_STATUS = {v: k for k, v in STATUS_HE.items()}
FUNNEL = ["new", "interested", "applied", "interview", "offer"]
VERDICT_HE = {"strong": "חזקה", "good": "טובה", "stretch": "מתיחה", "poor": "חלשה"}

st.set_page_config(page_title="Job Hunter", page_icon=":material/work_history:", layout="wide")
inject_theme()


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
    db.backfill_required_years()      # jobs saved before the experience filter existed
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
    df["required_years"] = pd.to_numeric(df["required_years"], errors="coerce")
    for col in ("matching_skills", "missing_skills"):
        df[col] = df[col].map(lambda v: v if isinstance(v, list) else [])
    return df.set_index("id", drop=False)


def refresh() -> None:
    load_jobs.clear()
    st.rerun()


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
        if st.button("בואו נמצא את המשרה הבאה", type="primary", width="stretch"):
            start_run()
            st.rerun()


def sidebar(df: pd.DataFrame) -> pd.DataFrame:
    max_years = load_config()["filters"].get("max_required_years")
    with st.sidebar:
        brand_header()
        st.html('<div class="jh-hello">הצעד הבא שלך מתחיל כאן.</div>'
                '<div class="jh-hello-sub">מכוונים את החיפוש, והסוכן יוצא למצוא הזדמנויות.</div>')
        with st.container(key="sb-launch"):
            run_panel()
            runs = db.last_runs(1)
            if runs:
                r, s = runs[0], runs[0]["stats"]
                when = to_il(r["finished"] or r["started"])
                failed = len(s.get("errors", []))
                st.html(f'<div class="jh-run-summary">ריצה אחרונה: {when:%d/%m %H:%M} · {s.get("duration_s", "?")} שנ׳ · '
                        f'{s.get("kept", 0)} חדשות · {failed} מקורות עם תקלה</div>')
        if df.empty:
            with st.container(key="sb-prefs"):
                theme_toggle()
            return df

        with st.container(key="sb-search"):
            question("מה מחפשים?")
            query = st.text_input("חיפוש חופשי (כותרת / חברה)", placeholder="כותרת משרה או שם חברה",
                                  label_visibility="collapsed")
        with st.container(key="sb-match"):
            st.html('<div class="jh-q-sub">ההתאמה שלך</div>'
                    f'<div class="jh-range"><span class="jh-range-num">{st.session_state.get("min_score", 60)}</span>'
                    '<span class="jh-range-label">ציון מינימלי</span></div>')
            min_score = st.slider("ציון מינימלי", 0, 100, 60, key="min_score", label_visibility="collapsed")
        with st.container(key="sb-source"):
            question("מאיפה מגיעות המשרות?")
            sources = st.multiselect("מקור", sorted(df["source"].unique()), placeholder="כל המקורות",
                                     label_visibility="collapsed")
        with st.container(key="sb-stage"):
            question("איפה אנחנו בתהליך?")
            statuses = st.pills("סטטוס", list(STATUS_HE.values()), selection_mode="multi",
                                default=[v for k, v in STATUS_HE.items() if k != "not_relevant"],
                                label_visibility="collapsed")
        with st.container(key="sb-where"):
            question("איפה תרצו לעבוד?")
            loc = st.pills("מיקום", ["הכול", "ישראל", "מרחוק"], selection_mode="single", default="הכול",
                           label_visibility="collapsed") or "הכול"
        with st.container(key="sb-recency"):
            question("פורסמו לאחרונה", "במספר הימים האחרונים")
            days = st.number_input("ימים", 1, 90, 60, step=5, format="%d", label_visibility="collapsed")
        with st.container(key="sb-prefs"):
            junior = st.toggle("רק משרות ללא דרישת ניסיון", value=True,
                               help="מסתיר משרות שמציינות שנות ניסיון נדרשות")
            only_new = st.toggle("רק חדשות ב־24 השעות האחרונות")
            theme_toggle()

    out = df[df["score"] >= min_score]
    if junior and max_years is not None:
        out = out[out["required_years"].fillna(0) <= max_years]
    if sources:
        out = out[out["source"].isin(sources)]
    if statuses:
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
    kpi_row([("משרות מתאימות", len(shown)), ("חדשות היום", int(shown["is_new"].sum())),
             ("התאמה חזקה (75+)", int((shown["score"] >= 75).sum())),
             ("הוגשה מועמדות", int((df["status"] == "applied").sum()))])
    st.space("small")

    if shown.empty:
        st.info("אין משרות שעונות על הסינון. נסו להוריד את הציון המינימלי.")
        return

    view = shown.sort_values("score", ascending=False).copy()
    view["verdict_he"] = [VERDICT_HE.get(v) or "ראשוני" for v in view["verdict"]]
    view["status_he"] = view["status"].map(STATUS_HE)
    view["title_flag"] = [("● " if n else "○ " if s else "") + t
                          for t, n, s in zip(view["title"], view["is_new"], view["stale"])]
    cols = ["score", "title_flag", "company", "where", "source", "age_days", "verdict_he", "status_he", "url"]
    table = view[cols]
    # RTL trick: the grid stays LTR (canvas), so columns are listed right-to-left in reverse
    edited = st.data_editor(
        table, hide_index=True, column_order=cols[::-1], height="content", row_height=44, key="jobs_editor",
        disabled=[c for c in cols if c != "status_he"],
        column_config={
            "score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d", width="small"),
            "title_flag": st.column_config.TextColumn("תפקיד", width="medium"),
            "company": "חברה", "where": "מיקום", "source": "מקור",
            "age_days": st.column_config.NumberColumn("ימים", format="%d", width="small"),
            "verdict_he": "הערכה",
            "status_he": st.column_config.SelectboxColumn("סטטוס", options=list(STATUS_HE.values()), required=True),
            "url": st.column_config.LinkColumn("קישור", display_text="פתח", width="small"),
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
    ids = list(view.index)
    labels = {i: f"{view.loc[i, 'score']:.0f} · {view.loc[i, 'title']} — {view.loc[i, 'company']}" for i in ids}
    job_id = st.selectbox("פרטי משרה", ids, format_func=labels.get)
    job = db.job_detail(job_id)
    if not job:
        return
    where = job["location"] or job["remote_region"] or ("Remote" if job["is_remote"] else "")
    with st.container(key="detail-card"):
        head_score, head_text = st.columns([1, 5], vertical_alignment="center")
        with head_score:
            score_box(job["score"] or 0)
        with head_text:
            st.html(f'<p class="jh-job-title">{html.escape(job["title"])}</p>'
                    f'<div class="jh-job-meta">{html.escape(job["company"])} · {html.escape(where)} · '
                    f'{html.escape(job["source"])}</div>')
        if job["verdict"]:
            st.html(f'<div class="jh-note">הערכה: {VERDICT_HE.get(job["verdict"], job["verdict"])} · '
                    f'{html.escape(job["scored_by"] or "")}</div>')
        else:
            st.html('<div class="jh-note">ציון ראשוני (חישוב אוטומטי). הערכת מודל שפה תתווסף כשהמפתח יופעל.</div>')
        if job["reasons"]:
            st.markdown(job["reasons"])
        if job["seniority_fit"]:
            st.markdown(f"**התאמת ותק:** {job['seniority_fit']}")
        good, gap = st.columns(2)
        with good:
            section_label("כישורים תואמים")
            if job["matching_skills"]:
                chips(job["matching_skills"], "good")
            else:
                st.caption("—")
        with gap:
            section_label("כישורים חסרים")
            if job["missing_skills"]:
                chips(job["missing_skills"], "gap")
            else:
                st.caption("—")
        if job["cv_tip"]:
            st.info(job["cv_tip"])
        notes = st.text_area("הערות", job["notes"] or "", height=90, key=f"notes_{job_id}")
        with st.container(horizontal=True, gap="small"):
            if st.button("שמור הערות", type="primary", key=f"save_{job_id}"):
                db.update_notes(job_id, notes)
                st.toast("נשמר")
                load_jobs.clear()
            if job["url"]:
                st.link_button("פתח את המשרה", job["url"])
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
        st.info('עוד לא הוגשו מועמדויות. שנו סטטוס בטבלת המשרות כדי לעקוב כאן.')
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
        st.info('אין עדיין נתוני כישורים חסרים. הם מגיעים מהערכת מודל השפה, '
                    'ויופיעו אחרי ריצה עם מפתח API פעיל.')
    if have:
        st.subheader("הכישורים שמתאימים הכי הרבה")
        st.plotly_chart(bar([h[0] for h in have], [h[1] for h in have], SEA), width="stretch")


def sources_tab() -> None:
    runs = db.last_runs(1)
    if not runs:
        st.info('עוד לא הייתה ריצה.')
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
        st.info('אין פרופיל עדיין. שימו את קורות החיים בתיקיית cv/ והריצו את הסוכן.')
        return
    p = latest["data"]
    heuristic = latest["cv_hash"].endswith(":heuristic")
    st.html(f'<p class="jh-job-title">{html.escape(p.get("name") or "—")}</p>'
            f'<div class="jh-job-meta">{html.escape(p.get("headline", ""))}</div>')
    st.caption(f"קובץ: {latest['cv_file']} · ותק: {p.get('seniority')} · {p.get('years_experience')} שנות ניסיון"
               + (" · פרופיל ראשוני (ללא מודל שפה)" if heuristic else ""))
    st.markdown("**כישורים**")
    chips(p.get("skills", []), "plain")
    st.markdown("**תפקידי יעד**")
    chips(p.get("target_roles", []), "good")
    st.info("כדי לתקן את החילוץ בלי לערוך את קורות החיים: config.yaml ← profile.overrides")


# ------------------------------------------------------------ main

def main() -> None:
    df = load_jobs()
    shown = sidebar(df)
    title("משרות")
    if df.empty:
        st.info('עוד אין משרות. שימו את קורות החיים בתיקיית cv/ ולחצו '
                    '"הרץ סוכן עכשיו".')
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
