"""Visual prototype of Figma frame 2:30 'Dashboard / Jobs' with static sample data."""
import pandas as pd
import streamlit as st
from ui.components import chips, inject_theme, kpi_row, score_box, section_label, title

st.set_page_config(page_title="Job Hunter", page_icon="🎯", layout="wide")
inject_theme()

STATUSES = ["חדש", "מעניין", "הוגשה מועמדות", "ראיון", "הצעה", "נדחה"]
rows = [
    (100, "Machine Learning Engineer", "Gotfriends", "Center District, Israel", "jobspy:linkedin", 1),
    (95, "Machine Learning Engineer", "Millennium", "Tel Aviv-Yafo, Tel Aviv District, Israel", "jobspy:linkedin", 1),
    (86, "Machine Learning Engineer", "Axon Pulse", "Tel Aviv District, Israel", "jobspy:linkedin", 5),
    (85, "Python Developer", "Gotfriends", "Center District, Israel", "jobspy:linkedin", 5),
    (79, "Generative AI Engineer", "Axon Pulse", "Ashdod, South District, Israel", "jobspy:linkedin", 2),
    (70, "Full Stack Engineer, AI Agents", "Riverside", "Tel Aviv-Yafo, Tel Aviv District, Israel", "jobspy:linkedin", 4),
    (68, "C++ Backend Software Engineer", "Infinidat", "Herzliya, Tel Aviv District, Israel", "jobspy:linkedin", 1),
    (67, "Java Software Engineer", "NGsoft", "Center District, Israel", "jobspy:linkedin", 2),
    (67, "Junior Data Scientist", "Mize", "TA, Israel ,יפו", "jobspy:indeed", 1),
    (62, "C++ Software Developer", "Mobileye", "Jerusalem District, Israel", "jobspy:linkedin", 2),
    (61, "C/C++ Software Engineer", "SQLink Group", "Yehud Monosson, Center District, Israel", "jobspy:linkedin", 6),
]
df = pd.DataFrame(rows, columns=["score", "title", "company", "location", "source", "age_days"])
df["verdict"], df["status"], df["url"] = "ראשוני", "חדש", "https://example.com"

# ---------------- sidebar ----------------
with st.sidebar:
    st.html('<div class="jh-brand">Job Hunter</div>')
    st.button("מצא משרה חדשה", type="primary", width="stretch")
    st.html('<div class="jh-run-summary">ריצה אחרונה: 13/10 17:07 · 5.9 שנ׳ · 0 חדשות · 0 מקורות עם תקלה</div>')
    st.divider()
    st.slider("ציון מינימלי", 0, 100, 60)
    st.multiselect("מקור", ["jobspy:linkedin", "jobspy:indeed", "greenhouse"], placeholder="בחרו אפשרויות")
    st.pills("סטטוס", STATUSES, selection_mode="multi", default=["חדש", "מעניין", "הוגשה מועמדות"])
    st.radio("מיקום", ["הכול", "ישראל", "מרחוק"], horizontal=True)
    st.slider("פורסמו ב-N הימים האחרונים", 1, 90, 60)
    st.text_input("חיפוש חופשי (כותרת / חברה)")
    st.toggle("רק חדשות (24 שעות)")

# ---------------- main ----------------
title("משרות")
tab_jobs, *_ = st.tabs(["משרות", "תהליך", "תובנות", "מקורות", "פרופיל"])
with tab_jobs:
    kpi_row([("משרות מתאימות", 12), ("חדשות היום", 12), ("התאמה חזקה (75+)", 5), ("הוגשה מועמדות", 0)])
    st.space("small")
    # RTL trick: the grid stays LTR (canvas), so list columns right-to-left in reverse
    order = ["url", "status", "verdict", "age_days", "source", "location", "company", "title", "score"]
    st.dataframe(
        df, hide_index=True, column_order=order, height="content", row_height=44,  # Figma row height 44px
        column_config={
            "score": st.column_config.ProgressColumn("ציון", min_value=0, max_value=100, format="%d", width="small"),
            "title": st.column_config.TextColumn("תפקיד", width="medium"),
            "company": "חברה", "location": "מיקום", "source": "מקור",
            "age_days": st.column_config.NumberColumn("ימים", width="small"),
            "verdict": "הערכה", "status": "סטטוס",
            "url": st.column_config.LinkColumn("קישור", display_text="פתח", width="small"),
        },
    )
    st.caption("ציון 'ראשוני' = הערכה אוטומטית ללא מודל שפה")

    with st.container(key="detail-card"):
        head_score, head_text = st.columns([1, 5], vertical_alignment="center")
        with head_score:
            score_box(100)
        with head_text:
            st.html('<p class="jh-job-title">Machine Learning Engineer</p>'
                    '<div class="jh-job-meta">Gotfriends · Center District, Israel · jobspy:linkedin</div>')
        st.html('<div class="jh-note">ציון ראשוני (חישוב אוטומטי). הערכת מודל שפה תתווסף כשהמפתח יופעל.</div>')
        good, gap = st.columns(2)
        with good:
            section_label("כישורים תואמים")
            chips(["SQL", "RAG", "LangChain", "PyTorch", "Python"], "good")
        with gap:
            section_label("כישורים חסרים")
            chips(["MLflow", "AWS", "Kubernetes"], "gap")
        st.info("טיפ: להציג ראשונים את פרויקט ה-RAG ואת הניסיון עם PyTorch, ולהוסיף את מילת המפתח MLOps.")
        st.text_area("הערות", height=90)
        with st.container(horizontal=True, gap="small"):
            st.button("שמור הערות", type="primary")
            st.link_button("פתח את המשרה", "https://example.com")
