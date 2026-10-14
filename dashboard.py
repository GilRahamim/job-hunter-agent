"""Streamlit dashboard: browse scored jobs, track applications. Hebrew UI, RTL.

Reads from SQLite; writes only `status` and `notes` (and, when asked, an uploaded CV / a new user).
One Streamlit process serves every browser session, so the selected user is passed explicitly
(USER, CFG, DB below) instead of through JOBHUNTER_USER."""
from __future__ import annotations

import html
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from jobhunter import db, handoff, stop
from jobhunter.config import ROOT, load_config, run_dir
from jobhunter.llm import llm_available
from jobhunter.models import CandidateProfile
from jobhunter.personalize import personalize
from jobhunter.runlock import lock_path, running_pid
from jobhunter.users import UserError, create_user, display_name, list_users, parse_titles, save_cv
from ui.components import (brand_header, chips, inject_theme, kpi_row, question, score_box,
                           section_label, theme_toggle, title)
from ui.tokens import DARK, LIGHT

IL = ZoneInfo("Asia/Jerusalem")

_scheme = getattr(getattr(st.context, "theme", None), "type", None) or "light"
_T = DARK if _scheme == "dark" else LIGHT
# charts: accent = good, gap color = missing skills (same tokens as the Figma design)
INK, SEA, CORAL, MIST = _T["ink"], _T["accent"], _T["gap_text"], _T["mist"]

STATUS_HE = {"new": "חדש", "interested": "מעניין", "applied": "הוגשה מועמדות", "interview": "ראיון",
             "offer": "הצעה", "rejected": "נדחה", "not_relevant": "לא רלוונטי"}
HE_STATUS = {v: k for k, v in STATUS_HE.items()}
GOAL_RANGE = (3, 10)            # agent mode: matches to find, chosen in the sidebar
STARTUP_GRACE_S = 20            # a run just launched may not have written run.lock yet
FORCE_STOP_AFTER_S = 60         # offer a hard stop when a graceful stop takes longer than this
WHERE = ["הכול", "ישראל", "מרחוק"]
MAX_DAYS = 365                  # the recency filter's range; the default shows everything
SENT = ("applied", "interview", "offer")   # statuses that mean "CV sent"
UNSENT = "interested"                      # where "undo sent" puts a job back
FUNNEL = ["new", "interested", "applied", "interview", "offer"]
VERDICT_HE = {"strong": "חזקה", "good": "טובה", "stretch": "מתיחה", "poor": "חלשה"}

CV_TYPES = ["pdf", "docx", "txt"]

st.set_page_config(page_title="Job Hunter", page_icon=":material/work_history:", layout="wide")
inject_theme()


# ------------------------------------------------------------ who is searching

def selected_user() -> str:
    """The user this browser session looks at: "" (the owner) or a users/<id> folder; kept in the URL."""
    ss = st.session_state
    if "user" not in ss:
        ss["user"] = st.query_params.get("user", "")
    if ss["user"] and ss["user"] not in list_users():
        ss["user"] = ""
    return ss["user"]


def search_config(user: str, path) -> dict:
    """The config this user's runs use: auto_from_cv users get the filters derived from their CV."""
    cfg = load_config(user)
    latest = db.latest_profile(path)
    return personalize(cfg, CandidateProfile(**latest["data"])) if latest else cfg


USER = selected_user()
DB = db.db_path(user=USER)
CFG = search_config(USER, DB)
LOG_PATH = run_dir(USER) / "logs" / "dashboard-run.log"


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
def load_jobs(path: str, cfg: dict) -> pd.DataFrame:
    db.backfill_required_years(path)      # jobs saved before the experience filter existed
    rows = db.jobs_table(path)
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
    df["junior_ok"] = ~df["id"].isin(db.not_junior_ids(cfg, path))
    for col in ("matching_skills", "missing_skills"):
        df[col] = df[col].map(lambda v: v if isinstance(v, list) else [])
    return df.set_index("id", drop=False)


def refresh() -> None:
    load_jobs.clear()
    st.rerun()


def is_running() -> int | None:
    return running_pid(USER)


# ------------------------------------------------------------ sidebar

def start_run(goal: int | None = None) -> None:
    """goal=None: the fixed pipeline; otherwise the tool-using agent with that goal."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "run_agent.py"] + (["--user", USER] if USER else []) \
        + (["--agent", "--goal", str(goal)] if goal else [])
    with open(LOG_PATH, "w", encoding="utf-8") as log:      # the child keeps its own handle
        subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    st.session_state["launched_at"] = time.time()


def force_stop(pid: int) -> None:
    """Last resort when a graceful stop takes too long: kill the run (its results are lost)."""
    try:
        os.kill(pid, signal.SIGTERM)          # TerminateProcess on Windows
    except OSError:
        pass
    lock_path(USER).unlink(missing_ok=True)
    stop.clear_stop(USER)


def _health_url(base: str) -> str:
    # Windows resolves "localhost" to IPv6 first and waits ~2s before trying 127.0.0.1
    return base.rstrip("/").replace("//localhost", "//127.0.0.1") + "/models"


@st.cache_data(ttl=15, show_spinner=False)
def local_llm_down(base: str | None) -> bool:
    """True when the agent's local model server (agent.llm.base_url) does not answer."""
    if not base:
        return False                                   # cloud provider: nothing local to check
    try:
        requests.get(_health_url(base), timeout=2).raise_for_status()
    except requests.RequestException:
        return True
    return False


def default_goal(cfg: dict) -> int:
    lo, hi = GOAL_RANGE
    return min(max(int(cfg["agent"].get("goal_matches", hi)), lo), hi)


def run_active() -> bool:
    return bool(is_running()) or time.time() - st.session_state.get("launched_at", 0) < STARTUP_GRACE_S


RUN_KEYS = ("launched_at", "stop_search", "stop_at", "force_offered")


def on_stop_toggle() -> None:
    """The "stop search" toggle: ask the running search to finish its step, save and stop."""
    if st.session_state.get("stop_search"):
        stop.request_stop(USER)
        st.session_state["stop_at"] = time.time()
    else:                                                  # switched back off before it stopped
        stop.clear_stop(USER)
        for key in ("stop_at", "force_offered"):
            st.session_state.pop(key, None)


@st.fragment(run_every=3)
def run_status() -> None:
    """Live log while a run is going; only this fragment polls, the controls stay still."""
    if not run_active():
        for key in RUN_KEYS:
            st.session_state.pop(key, None)
        stop.clear_stop(USER)
        load_jobs.clear()
        st.rerun(scope="app")
    stop_at = st.session_state.get("stop_at")
    if stop_at:
        st.info("עוצר… המשרות שכבר נמצאו יישמרו.")
        if (is_running() and time.time() - stop_at > FORCE_STOP_AFTER_S
                and not st.session_state.get("force_offered")):
            st.session_state["force_offered"] = True       # the controls (outside) show the hard stop
            st.rerun(scope="app")
    else:
        st.info("הסוכן רץ עכשיו…" if is_running() else "הסוכן מתחיל…")
    if LOG_PATH.exists():
        st.code("\n".join(LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]),
                language=None)


def run_controls(cfg: dict) -> None:
    if run_active():
        st.toggle("עצירת החיפוש", key="stop_search", on_change=on_stop_toggle,
                  help="הסוכן מסיים את הצעד הנוכחי, שומר את המשרות שכבר מצא ועוצר.")
        pid = is_running()
        if pid and st.session_state.get("force_offered"):
            st.button("עצירה מיידית", icon=":material/stop_circle:", on_click=force_stop, args=(pid,),
                      help="הסוכן לא נעצר בזמן. עצירה מיידית לא שומרת את התוצאות של הריצה הזו.")
        run_status()
        return
    goal, down, smart = None, False, False
    if not cfg.get("auto_from_cv"):            # the agent loop is tuned for the owner's search
        smart = st.toggle("סוכן חכם (המודל בוחר חיפושים)", key="agent_mode",
                          help="המודל המקומי כותב את החיפושים, קורא משרות ושומר את המתאימות. "
                               "איטי יותר מהחיפוש הרגיל.")
    if smart:
        goal = st.slider("כמה משרות מתאימות למצוא", *GOAL_RANGE, key="agent_goal",
                         help=f"הסוכן עוצר אחרי שמצא משרות בציון {cfg['agent']['min_match_score']} ומעלה, "
                              "או כשנגמרים החיפושים.")
        down = local_llm_down((cfg["agent"].get("llm") or {}).get("base_url"))
        if down:
            st.warning("המודל המקומי לא זמין. יש להפעיל את LM Studio ולטעון את המודל.",
                       icon=":material/warning:")
    st.button("בואו נמצא את המשרה הבאה", type="primary", width="stretch", disabled=down,
              on_click=start_run, args=(goal,))


def run_summary_html(run: dict) -> str:
    """Two short lines; every number is isolated with <bdi> so Hebrew and digits keep their order."""
    s = run["stats"]
    when = to_il(run["finished"] or run["started"])
    secs = float(s.get("duration_s") or 0)
    took = f"<bdi>{secs / 60:.1f}</bdi> דק׳" if secs >= 60 else f"<bdi>{secs:.0f}</bdi> שנ׳"
    failed = len(s.get("errors", []))
    parts = [f"<bdi>{s.get('kept', 0)}</bdi> חדשות"]
    if failed:
        parts.append("מקור אחד עם תקלה" if failed == 1 else f"<bdi>{failed}</bdi> מקורות עם תקלה")
    if s.get("llm_failed"):
        parts.append(f"<bdi>{s['llm_failed']}</bdi> בלי ציון AI")
    return (f'<div class="jh-run-summary">ריצה אחרונה: <bdi>{when:%d/%m %H:%M}</bdi> · {took}<br>'
            f'{" · ".join(parts)}</div>')


def llm_failure_notice(stats: dict) -> None:
    """Scoring failures are silent otherwise: jobs still show, only with the keyword score."""
    failed, err = stats.get("llm_failed", 0), stats.get("llm_error") or ""
    if not failed:
        return
    if "credit balance" in err.lower():
        why = "נגמר הקרדיט בחשבון ה-API. אפשר להטעין ב-console.anthropic.com (Plans & Billing)."
    elif "api key" in err.lower() or "authentication" in err.lower():
        why = "מפתח ה-API לא תקין. כדאי לבדוק את הקובץ .env."
    else:
        why = "הפירוט נמצא ביומן הריצה."
    st.warning(f"ציון ה-AI נכשל ב-{failed} משרות, ולכן הן קיבלו רק ציון לפי מילות מפתח. {why}",
               icon=":material/warning:")


# ------------------------------------------------------------ sidebar settings, kept in the URL
# A reload (the theme switch reloads the page) or a bookmark keeps the filters and the run mode.

def pref_defaults(cfg: dict) -> dict:
    # Nothing is hidden by default: every stored job shows until the owner narrows the view.
    return {"q": "", "min_score": 0, "sources": [], "where": "הכול", "days": MAX_DAYS, "junior": False,
            "only_new": False, "agent_mode": False, "agent_goal": default_goal(cfg),
            "stages": list(STATUS_HE.values())}


def _valid(key: str, value, default, df: pd.DataFrame):
    if key == "min_score":
        return min(max(value, 0), 100)
    if key == "days":
        return min(max(value, 1), MAX_DAYS)
    if key == "agent_goal":
        return min(max(value, GOAL_RANGE[0]), GOAL_RANGE[1])
    if key == "where":
        return value if value in WHERE else default
    if key == "sources":
        return [v for v in value if v in set(df["source"])] if not df.empty else []
    if key == "stages":
        return [v for v in value if v in STATUS_HE.values()]
    return value


def init_prefs(defaults: dict, df: pd.DataFrame) -> None:
    """Seed widget state from the URL when a widget has no state yet (widgets then take only a key)."""
    qp = st.query_params
    for key, default in defaults.items():
        if key in st.session_state:
            continue
        value = default
        if key in qp:
            try:
                if isinstance(default, bool):
                    value = qp[key] == "1"
                elif isinstance(default, int):
                    value = int(qp[key])
                elif isinstance(default, list):
                    value = qp.get_all(key)
                else:
                    value = qp[key]
            except ValueError:
                value = default
        st.session_state[key] = _valid(key, value, default, df)


def save_prefs(defaults: dict) -> None:
    """Write non-default settings to the URL; defaults are left out to keep it short."""
    qp = st.query_params
    for key, default in defaults.items():
        value = st.session_state.get(key, default)
        if value == default or value is None:
            if key in qp:
                del qp[key]
        elif isinstance(value, bool):
            qp[key] = "1" if value else "0"
        elif isinstance(value, list):
            qp[key] = value if value else ["-"]          # an empty multi-select is not the default
        else:
            qp[key] = str(value)


def sidebar(df: pd.DataFrame) -> pd.DataFrame:
    cfg = CFG
    defaults = pref_defaults(cfg)
    init_prefs(defaults, df)
    with st.sidebar:
        brand_header()
        st.html('<div class="jh-hello">הצעד הבא שלך מתחיל כאן.</div>'
                '<div class="jh-hello-sub">מכוונים את החיפוש, והסוכן יוצא למצוא הזדמנויות.</div>')
        user_picker()
        with st.container(key="sb-launch"):
            run_controls(cfg)
            runs = db.last_runs(1, DB)
            if runs:
                st.html(run_summary_html(runs[0]))
                llm_failure_notice(runs[0]["stats"])
        if df.empty:
            with st.container(key="sb-prefs"):
                theme_toggle()
            save_prefs(defaults)
            return df

        with st.container(key="sb-search"):
            question("מה מחפשים?")
            query = st.text_input("חיפוש חופשי (כותרת / חברה)", placeholder="כותרת משרה או שם חברה",
                                  key="q", label_visibility="collapsed")
        with st.container(key="sb-match"):
            st.html('<div class="jh-q-sub">ההתאמה שלך</div>'
                    f'<div class="jh-range"><span class="jh-range-num">{st.session_state["min_score"]}</span>'
                    '<span class="jh-range-label">ציון מינימלי</span></div>')
            min_score = st.slider("ציון מינימלי", 0, 100, key="min_score", label_visibility="collapsed")
        with st.container(key="sb-source"):
            question("מאיפה מגיעות המשרות?")
            sources = st.multiselect("מקור", sorted(df["source"].unique()), placeholder="כל המקורות",
                                     key="sources", label_visibility="collapsed")
        with st.container(key="sb-stage"):
            question("איפה אנחנו בתהליך?")
            statuses = st.pills("סטטוס", list(STATUS_HE.values()), selection_mode="multi", key="stages",
                                label_visibility="collapsed")
        with st.container(key="sb-where"):
            question("איפה תרצו לעבוד?")
            loc = st.pills("מיקום", WHERE, selection_mode="single", key="where",
                           label_visibility="collapsed") or "הכול"
        with st.container(key="sb-recency"):
            question("פורסמו לאחרונה", "במספר הימים האחרונים")
            days = st.number_input("ימים", 1, MAX_DAYS, step=5, format="%d", key="days", label_visibility="collapsed")
        with st.container(key="sb-prefs"):
            junior = experience_toggle(cfg["filters"])
            only_new = st.toggle("רק חדשות ב־24 השעות האחרונות", key="only_new")
            theme_toggle()
    save_prefs(defaults)

    out = df[df["score"] >= min_score]
    if junior:
        out = out[out["junior_ok"]]
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


def experience_toggle(f: dict) -> bool:
    """The "experience limit" view toggle, worded for this user's limit; none when there is no limit."""
    years, senior = f.get("max_required_years"), f.get("exclude_senior")
    if years is None and not senior:
        return False                      # an experienced user without a limit: nothing to hide
    if years is None:
        label, hides = "בלי משרות בכירות", "משרות בכירות"
    elif not years:
        label, hides = "רק משרות ללא דרישת ניסיון", "משרות בכירות ומשרות שדורשות ניסיון"
    else:
        label, hides = f"רק משרות עד {years:g} שנות ניסיון", f"משרות שדורשות יותר מ־{years:g} שנות ניסיון"
    return st.toggle(label, key="junior", help=f"מסתיר {hides}")


# ------------------------------------------------------------ tabs

def jobs_tab(df: pd.DataFrame, shown: pd.DataFrame) -> None:
    kpi_row([("משרות מתאימות", len(shown)), ("חדשות היום", int(shown["is_new"].sum())),
             ("התאמה חזקה (75+)", int((shown["score"] >= 75).sum())),
             ("קו״ח נשלחו", int(df["status"].isin(SENT).sum()))])
    st.space("small")

    if shown.empty:
        st.info("אין משרות שעונות על הסינון. נסו להוריד את הציון המינימלי.")
        return

    view = shown.sort_values("score", ascending=False).copy()
    view["verdict_he"] = [VERDICT_HE.get(v) or "ראשוני" for v in view["verdict"]]
    view["status_he"] = view["status"].map(STATUS_HE)
    view["sent"] = view["status"].isin(SENT)
    view["title_flag"] = [("● " if n else "○ " if s else "") + t
                          for t, n, s in zip(view["title"], view["is_new"], view["stale"])]
    cols = ["score", "title_flag", "company", "where", "source", "age_days", "verdict_he", "sent", "status_he", "url"]
    table = view[cols]
    # RTL trick: the grid stays LTR (canvas), so columns are listed right-to-left in reverse
    edited = st.data_editor(
        table, hide_index=True, column_order=cols[::-1], height="content", row_height=44, key="jobs_editor",
        disabled=[c for c in cols if c not in ("status_he", "sent")],
        column_config={
            "score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d", width="small"),
            "title_flag": st.column_config.TextColumn("תפקיד", width="medium"),
            "company": "חברה", "where": "מיקום", "source": "מקור",
            "age_days": st.column_config.NumberColumn("ימים", format="%d", width="small"),
            "verdict_he": "הערכה",
            "sent": st.column_config.CheckboxColumn("נשלחו קו״ח", width="small",
                                                    help="סמנו כששלחתם קורות חיים למשרה"),
            "status_he": st.column_config.SelectboxColumn("סטטוס", options=list(STATUS_HE.values()), required=True),
            "url": st.column_config.LinkColumn("קישור", display_text="פתח", width="small"),
        })
    changed = table_changes(table, edited)
    for job_id, status in changed.items():
        db.update_status(job_id, status, path=DB)
    if changed:
        st.toast("נשמר")
        refresh()
    st.caption("● = חדשה (24 שעות) · ○ = לא נראתה מעל שבועיים, ייתכן שנסגרה · ציון 'ראשוני' = הערכה אוטומטית ללא מודל שפה")
    detail_panel(view)


def table_changes(table: pd.DataFrame, edited: pd.DataFrame) -> dict[str, str]:
    """New status per edited row. Ticking "CV sent" marks the job applied (and records the date);
    unticking puts it back to interested. A status picked in the status column wins."""
    out = {}
    for job_id in edited.index:
        if edited.loc[job_id, "status_he"] != table.loc[job_id, "status_he"]:
            out[job_id] = HE_STATUS[edited.loc[job_id, "status_he"]]
        elif bool(edited.loc[job_id, "sent"]) != bool(table.loc[job_id, "sent"]):
            out[job_id] = "applied" if edited.loc[job_id, "sent"] else UNSENT
    return out


def set_status(job_id: str, status: str, message: str) -> None:
    db.update_status(job_id, status, path=DB)
    load_jobs.clear()
    st.toast(message)


def sent_controls(job: dict) -> None:
    """The "CV sent" button, or when it was sent and an undo."""
    if job["status"] in SENT:
        when = to_il(job["status_updated"])
        st.html(f'<div class="jh-note">קו״ח נשלחו{f" ב־<bdi>{when:%d/%m/%Y}</bdi>" if when else ""} · '
                f'{STATUS_HE[job["status"]]}</div>')
        st.button("בטל סימון שליחה", key=f"unsend_{job['id']}", on_click=set_status,
                  args=(job["id"], UNSENT, "הסימון בוטל"))
    else:
        st.button("שלחתי קורות חיים", type="primary", icon=":material/send:", key=f"send_{job['id']}",
                  on_click=set_status, args=(job["id"], "applied", "סומן: קו״ח נשלחו"),
                  help="מסמן את המשרה כ״הוגשה מועמדות״ ושומר את תאריך השליחה")


def detail_panel(view: pd.DataFrame) -> None:
    ids = list(view.index)
    labels = {i: f"{view.loc[i, 'score']:.0f} · {view.loc[i, 'title']} — {view.loc[i, 'company']}" for i in ids}
    job_id = st.selectbox("פרטי משרה", ids, format_func=labels.get)
    job = db.job_detail(job_id, DB)
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
            sent_controls(job)
            if st.button("שמור הערות", key=f"save_{job_id}"):
                db.update_notes(job_id, notes, DB)
                st.toast("נשמר")
                load_jobs.clear()
            if job["url"]:
                st.link_button("פתח את המשרה", job["url"])
        claude_panel(job)
        with st.expander("תיאור המשרה המלא"):
            st.text(job["description"] or "—")


# ------------------------------------------------------------ hand a job to Claude (subscription)

def prepare_brief(job_id: str) -> None:
    try:
        handoff.write_brief(job_id, USER, DB)
    except (handoff.HandoffError, OSError) as e:
        st.session_state["brief_msg"] = ("error", str(e))


def open_claude(brief) -> None:
    try:
        handoff.launch_claude(brief)
    except handoff.HandoffError as e:
        st.session_state["brief_msg"] = ("error", str(e))
        return
    st.session_state["brief_msg"] = ("success", "Claude Code נפתח בחלון חדש. כשהוא מסיים, הקבצים יופיעו כאן.")


def claude_panel(job: dict) -> None:
    """The writing for one job goes to Claude on the person's subscription, not the API."""
    folder = handoff.job_folder(job, DB)
    brief = folder / handoff.BRIEF
    with st.expander("הכנת מועמדות עם Claude", icon=":material/auto_awesome:", expanded=brief.exists()):
        st.caption("Claude מקבל את המשרה, את קורות החיים ואת ניתוח ההתאמה, ומכין קו״ח מותאמים, מכתב מקדים, "
                   "הכנה לראיון ורשימת פערים, בלי להוסיף שום דבר שלא כתוב בקורות החיים. "
                   "העבודה נספרת במנוי Claude שלך (Claude Code או claude.ai), לא ב-API.")
        st.button("עדכון התיק" if brief.exists() else "הכנת תיק למשרה", icon=":material/folder_open:",
                  key=f"brief_{job['id']}", on_click=prepare_brief, args=(job["id"],))
        show_message("brief_msg")
        if not brief.exists():
            return
        with st.container(horizontal=True, gap="small"):
            if handoff.can_launch():
                st.button("פתיחה ב-Claude Code", type="primary", icon=":material/terminal:",
                          key=f"claude_{job['id']}", on_click=open_claude, args=(brief,))
            st.download_button("הורדת התיק ל-claude.ai", brief.read_bytes(), file_name=f"{folder.name}.md",
                               mime="text/markdown", icon=":material/download:", on_click="ignore",
                               key=f"dl_brief_{job['id']}")
        if not handoff.claude_path():
            st.caption("Claude Code לא מותקן במחשב הזה. אפשר לצרף את התיק לשיחה חדשה ב-claude.ai.")
        st.caption("או בטרמינל, בתיקיית הפרויקט:")
        st.code(handoff.shell_command(brief), language=None)
        files = handoff.kit_files(folder)
        if files:
            section_label("מה Claude הכין")
            with st.container(horizontal=True, gap="small"):
                for f in files:
                    st.download_button(f.name, f.read_bytes(), file_name=f.name, on_click="ignore",
                                       icon=":material/description:", key=f"dl_{job['id']}_{f.name}")


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
    seen = df.dropna(subset=["first_seen_il"])
    per_day = seen.groupby(seen["first_seen_il"].map(lambda d: d.date())).size()
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
    runs = db.last_runs(1, DB)
    if not runs:
        st.info('עוד לא הייתה ריצה.')
        return
    health = pd.DataFrame(db.health_for_run(runs[0]["id"], DB))
    if health.empty:
        return
    warnings = health["warning"] if "warning" in health else pd.Series(None, index=health.index)
    health["מצב"] = [f"תקלה: {e}" if e else f"תקין ({w})" if w else "תקין"
                     for e, w in zip(health["error"], warnings)]
    st.dataframe(health[["source", "fetched", "duration_s", "מצב"]].rename(
        columns={"source": "מקור", "fetched": "נשלפו", "duration_s": "שניות"}), hide_index=True, width="stretch")
    hist = pd.DataFrame(db.health_history(14, DB))
    if not hist.empty and hist["run_id"].nunique() > 1:
        st.subheader("נשלפו לפי ריצה")
        st.line_chart(hist.pivot_table(index="run_id", columns="source", values="fetched"))


def profile_tab() -> None:
    latest = db.latest_profile(DB)
    if latest:
        profile_view(latest)
    else:
        st.info("אין פרופיל עדיין. מעלים קורות חיים כאן למטה ולוחצים על \"בואו נמצא את המשרה הבאה\".")
    st.divider()
    left, right = st.columns(2, gap="large")
    with left:
        cv_upload_form()
    with right:
        add_user_form()


def profile_view(latest: dict) -> None:
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
    if CFG.get("auto_from_cv") and CFG["search"].get("queries"):
        st.caption(f"התפקידים בחיפוש: {', '.join(CFG['search']['queries'])}")
    st.info("כדי לתקן את החילוץ בלי לערוך את קורות החיים: config.yaml ← profile.overrides")


# ------------------------------------------------------------ users and CV upload

def owner_label() -> str:
    latest = db.latest_profile(db.db_path(user=""))
    return (latest or {}).get("data", {}).get("name") or "המשתמש הראשי"


def switch_user(user: str) -> None:
    """Start the other user's view clean: filters, table edits and run state belong to one user."""
    ss = st.session_state
    keep = {"user", "dark_mode"}
    for key in [k for k in ss if k not in keep]:
        del ss[key]
    ss["user"] = user
    for key in [k for k in st.query_params if k != "user"]:
        del st.query_params[key]


def user_picker() -> None:
    users = list_users()
    if not users:
        return
    labels = {"": owner_label(), **{u: display_name(u) for u in users}}
    with st.container(key="sb-user"):
        question("מי מחפש/ת?")
        st.selectbox("משתמש", list(labels), key="user", format_func=labels.get, label_visibility="collapsed",
                     on_change=lambda: switch_user(st.session_state["user"]))


def on_add_user() -> None:
    ss = st.session_state
    upload = ss.get("new_user_cv")
    titles = parse_titles(ss.get("new_user_titles", ""))
    if upload is None:
        ss["add_user_msg"] = ("error", "נא לבחור קובץ קורות חיים.")
        return
    if not titles and not llm_available(load_config("")):
        ss["add_user_msg"] = ("error", "בלי מודל שפה צריך לכתוב לפחות תפקיד אחד לחיפוש.")
        return
    try:
        user = create_user(ss.get("new_user_name", ""), upload.name, upload.getvalue(), titles)
    except UserError as e:
        ss["add_user_msg"] = ("error", str(e))
        return
    switch_user(user)
    ss["add_user_msg"] = ("success", f"נוצר חיפוש עבור {display_name(user)}. "
                                     "עכשיו לוחצים על \"בואו נמצא את המשרה הבאה\".")


def add_user_form() -> None:
    section_label("הוספת אדם נוסף")
    st.caption("לכל אחד חיפוש משלו: קורות חיים, משרות וסטטוסים נפרדים. "
               "התפקידים לחיפוש נלקחים מקורות החיים.")
    with st.form("add_user", clear_on_submit=True, border=False):
        st.text_input("שם", key="new_user_name")
        st.file_uploader("קורות חיים (PDF / DOCX / TXT)", type=CV_TYPES, key="new_user_cv")
        st.text_area("תפקידים לחיפוש (לא חובה, מופרדים בפסיקים)", key="new_user_titles", height=70,
                     help="ריק = התפקידים שמודל השפה מציע לפי קורות החיים. בלי מודל שפה זה שדה חובה.")
        st.form_submit_button("יצירת חיפוש", type="primary", icon=":material/person_add:", on_click=on_add_user)
    show_message("add_user_msg")


def on_cv_upload() -> None:
    ss = st.session_state
    upload = ss.get("cv_upload")
    if upload is None:
        ss["cv_upload_msg"] = ("error", "נא לבחור קובץ.")
        return
    try:
        save_cv(USER, upload.name, upload.getvalue())
    except UserError as e:
        ss["cv_upload_msg"] = ("error", str(e))
        return
    ss["cv_upload_msg"] = ("success", "קורות החיים נשמרו. הריצה הבאה תקרא אותם ותדרג מחדש את המשרות.")


def cv_upload_form() -> None:
    section_label("קורות חיים חדשים")
    st.caption("הקובץ החדש מחליף את הקודם בריצה הבאה, והמשרות מדורגות מחדש לפיו.")
    with st.form("cv_upload_form", clear_on_submit=True, border=False):
        st.file_uploader("קובץ קורות חיים", type=CV_TYPES, key="cv_upload")
        st.form_submit_button("שמירת קורות החיים", icon=":material/upload_file:", on_click=on_cv_upload)
    show_message("cv_upload_msg")


def show_message(key: str) -> None:
    msg = st.session_state.pop(key, None)
    if msg:
        (st.success if msg[0] == "success" else st.error)(msg[1])


# ------------------------------------------------------------ main

def main() -> None:
    df = load_jobs(str(DB), CFG)
    shown = sidebar(df)
    if USER:
        st.query_params["user"] = USER
    elif "user" in st.query_params:
        del st.query_params["user"]
    title("משרות")
    if df.empty:
        st.info('עוד אין משרות. מעלים קורות חיים בלשונית "פרופיל" ולוחצים '
                '"בואו נמצא את המשרה הבאה".')
        t_prof, t_src = st.tabs(["פרופיל", "מקורות"])
        with t_prof:
            profile_tab()
        with t_src:
            sources_tab()
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
