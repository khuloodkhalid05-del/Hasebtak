"""
dashboard/app.py
Streamlit Analytics Dashboard for Hasebtak (حسبتك).
Designed for Ministry of Finance policymakers to track citizen sentiment,
OBS 2025 participation indicators, and budget allocation insights.
"""

import os
import sys
import json
import base64
import pandas as pd
import streamlit as st

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.polls import PollEngine
from core.grounding import GroundingEngine
from core.router import HasebtakCore
from core.voice import text_to_speech

# Helper to encode images to base64 for reliable rendering
def get_image_base64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
mof_badge_b64 = get_image_base64(os.path.join(ASSETS_DIR, "mof_badge.png"))
trans_badge_b64 = get_image_base64(os.path.join(ASSETS_DIR, "transparency_badge.png"))
hero_bg_b64 = get_image_base64(os.path.join(ASSETS_DIR, "mof_hero_bg.jpg"))

st.set_page_config(
    page_title="حسبتك | لوحة تحكم موازنة المواطن",
    page_icon="🇪🇬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern Egyptian Government look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
    * {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .metric-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .kpi-val {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e3c72;
    }
    .kpi-title {
        color: #64748b;
        font-size: 0.95rem;
        font-weight: 600;
    }
    .accessible-box {
        padding: 20px;
        border-radius: 14px;
        color: white !important;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 12px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .box-blue { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); }
    .box-green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
    .box-orange { background: linear-gradient(135deg, #f12711 0%, #f5af19 100%); }
    .box-purple { background: linear-gradient(135deg, #8e2de2 0%, #4a00e0 100%); }
</style>
""", unsafe_allow_html=True)

# Official Clean Header (Right: Ministry of Finance | Center: Hasebtak Title | Left: Transparency Unit)
bg_banner_css = f"background: linear-gradient(180deg, rgba(15, 23, 42, 0.35) 0%, rgba(15, 23, 42, 0.15) 50%, rgba(15, 23, 42, 0.65) 100%), url('data:image/jpeg;base64,{hero_bg_b64}') center 35% / cover no-repeat;" if hero_bg_b64 else "background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);"

header_html = f"""
<div style="{bg_banner_css} border: 1.5px solid rgba(217, 119, 6, 0.65); border-radius: 20px; min-height: 240px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 14px 35px rgba(0,0,0,0.4); display: flex; flex-direction: column; justify-content: space-between; direction: rtl; position: relative;">
    <!-- Top Row: ONLY the two circular logos (Right: MOF, Left: Transparency Unit) -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; width: 100%;">
        <!-- Right: Ministry of Finance Logo ONLY -->
        <div style="flex: 0 0 auto; background: rgba(255, 255, 255, 0.12); backdrop-filter: blur(8px); border-radius: 50%; padding: 4px; border: 2px solid rgba(245, 158, 11, 0.7); box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
            <img src="data:image/png;base64,{mof_badge_b64}" style="width: 78px; height: 78px; object-fit: contain;" alt="وزارة المالية" />
        </div>

        <!-- Left: Transparency Unit Logo ONLY -->
        <div style="flex: 0 0 auto; background: rgba(255, 255, 255, 0.12); backdrop-filter: blur(8px); border-radius: 50%; padding: 4px; border: 2px solid rgba(245, 158, 11, 0.7); box-shadow: 0 4px 14px rgba(0,0,0,0.4);">
            <img src="data:image/png;base64,{trans_badge_b64}" style="width: 78px; height: 78px; object-fit: contain;" alt="وحدة الشفافية والمشاركة المجتمعية" />
        </div>
    </div>

    <!-- Bottom Row: Title Horizontally across with year underneath -->
    <div style="width: 100%; text-align: center; margin-top: auto; padding-top: 14px; padding-bottom: 6px;">
        <div style="display: inline-block; text-align: center; background: rgba(15, 23, 42, 0.70); backdrop-filter: blur(10px); padding: 8px 36px; border-radius: 24px; border: 1px solid rgba(255, 255, 255, 0.2); box-shadow: 0 6px 20px rgba(0,0,0,0.45);">
            <h1 style="text-align: center; color: #ffffff; margin: 0; font-size: 1.75rem; font-weight: 800; letter-spacing: -0.2px; text-shadow: 0 2px 8px rgba(0,0,0,0.9); white-space: nowrap;">
                منصة "حسبتك" — لوحة متابعة موازنة المواطن
            </h1>
            <div style="text-align: center; color: #f59e0b; margin-top: 2px; font-size: 1.25rem; font-weight: 800; letter-spacing: 1px; text-shadow: 0 2px 6px rgba(0,0,0,0.85);">
                2026 / 2027
            </div>
        </div>
    </div>
</div>
"""
st.html(header_html)

poll_engine = PollEngine()
grounding_engine = GroundingEngine()

# Sidebar: Welcome Message (without logos, exactly as requested)
sidebar_header_html = """
<div style="text-align: center; background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%); padding: 18px 14px; border-radius: 14px; margin-bottom: 20px; border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
    <div style="font-size: 1.02rem; font-weight: 700; color: #f8fafc; line-height: 1.6;">
        مرحباً بك مع المستشار الرقمي لموازنة المواطن 2026/2027
    </div>
</div>
"""
st.sidebar.html(sidebar_header_html)

# Sidebar Navigation
st.sidebar.title("📌 أقسام المنظومة")
page = st.sidebar.radio(
    "انتقل إلى:",
    [
        "📊 نبض المواطن ومؤشرات OBS",
        "💰 مخصصات موازنة 2026/2027",
        "🔍 مستكشف الأرقام المؤكدة (Facts Ledger)",
        "💬 محاكي المحادثة والتحقق (Live Demo)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **أمان المعلومات:**\n"
    "- تشفير أحادي الاتجاه (SHA-256) للمشاركين.\n"
    "- عدم تسجيل أي بيانات شخصية (Zero PII).\n"
    "- حاجز أمان حسابي صارم ضد الهلوسة (Numeric Guardrail)."
)

# PAGE 1: نبض المواطن ومؤشرات OBS
if page == "📊 نبض المواطن ومؤشرات OBS":
    st.subheader("📈 مؤشرات مسح الموازنة المفتوحة الدولي (OBS 2025)")
    st.caption("النتائج الرسمية المنشورة في يونيو 2026 مقارنة بعام 2023:")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="مؤشر الشفافية (Transparency)", value="59 / 100", delta="+10 نقاط (من 49)")
    with col2:
        st.metric(label="مؤشر الرقابة (Oversight)", value="59 / 100", delta="+5 نقاط (من 54)")
    with col3:
        st.metric(label="مؤشر المشاركة (Participation)", value="35 / 100", delta="المستهدف رفعه بـ 'حسبتك'", delta_color="inverse")
    with col4:
        st.metric(label="الترتيب العالمي لمصر", value="#22 - 23", delta="صعود 10 مراكز عالمياً")

    st.markdown("---")
    st.subheader("🗳️ نبض المواطن (Citizen's Pulse) — استطلاع الرأي النشط")

    active_poll = poll_engine.get_active_poll()
    if active_poll:
        poll_id = active_poll["id"]
        stats = poll_engine.get_poll_stats(poll_id)

        st.markdown(f"**سؤال الأسبوع:** {active_poll['question_ar']}")
        st.caption(f"المجال: {active_poll['topic']} | إجمالي المشاركات المسجلة: {stats['total_votes']} مشاركة")

        if stats["options"]:
            df_poll = pd.DataFrame(stats["options"])
            df_poll = df_poll.rename(columns={"text": "الخيار", "votes": "الأصوات", "percentage": "النسبة %"})

            col_poll, col_demographics = st.columns(2)
            with col_poll:
                palette_bars = [
                    ("linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)", "#38bdf8", "rgba(56, 189, 248, 0.15)"),
                    ("linear-gradient(90deg, #0369a1 0%, #0ea5e9 100%)", "#0ea5e9", "rgba(14, 165, 233, 0.15)"),
                    ("linear-gradient(90deg, #4338ca 0%, #6366f1 100%)", "#818cf8", "rgba(129, 140, 248, 0.15)"),
                    ("linear-gradient(90deg, #6d28d9 0%, #8b5cf6 100%)", "#a78bfa", "rgba(167, 139, 250, 0.15)"),
                    ("linear-gradient(90deg, #d97706 0%, #f59e0b 100%)", "#f59e0b", "rgba(245, 158, 11, 0.15)")
                ]
                html_options = ""
                for idx, row in df_poll.iterrows():
                    grad, text_c, bg_pill = palette_bars[idx % len(palette_bars)]
                    opt_text = row["الخيار"]
                    votes_val = int(row["الأصوات"])
                    pct_val = float(row["النسبة %"])
                    bar_w = max(pct_val, 4.0) if votes_val > 0 else 0
                    html_options += f"""
                    <div style="margin-bottom: 12px; background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <div style="font-size: 0.96rem; font-weight: 700; color: #f8fafc; line-height: 1.5;">
                                {opt_text}
                            </div>
                            <div style="font-size: 0.88rem; font-weight: 800; color: {text_c}; background: {bg_pill}; border: 1px solid {text_c}44; padding: 3px 12px; border-radius: 16px; white-space: nowrap;">
                                {votes_val} أصوات ({pct_val:.1f}%)
                            </div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border-radius: 8px; height: 12px; width: 100%; overflow: hidden; padding: 1px;">
                            <div style="background: {grad}; width: {bar_w}%; height: 100%; border-radius: 6px; box-shadow: 0 0 8px {text_c}55;"></div>
                        </div>
                    </div>
                    """
                
                poll_card_html = f"""
                <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 16px; padding: 18px 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.35); user-select: none;">
                    <div style="font-size: 1.08rem; font-weight: 800; color: #f8fafc; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                        🗳️ نتائج تصويت المواطنين على الأولويات
                    </div>
                    {html_options}
                </div>
                """
                st.html(poll_card_html)

            with col_demographics:
                try:
                    with open(poll_engine.votes_path, "r", encoding="utf-8") as f:
                        raw_votes = json.load(f)
                    if raw_votes:
                        df_v = pd.DataFrame(raw_votes)
                        prof_counts = df_v["user_profile"].value_counts().reset_index()
                        prof_counts.columns = ["الفئة الاجتماعية", "عدد المشاركين"]
                        total_prof = prof_counts["عدد المشاركين"].sum()
                        prof_counts["النسبة %"] = (prof_counts["عدد المشاركين"] / total_prof * 100).round(1)

                        prof_palette = [
                            ("linear-gradient(90deg, #d97706 0%, #f59e0b 100%)", "#f59e0b", "rgba(245, 158, 11, 0.15)"),
                            ("linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)", "#38bdf8", "rgba(56, 189, 248, 0.15)"),
                            ("linear-gradient(90deg, #059669 0%, #10b981 100%)", "#10b981", "rgba(16, 185, 129, 0.15)"),
                            ("linear-gradient(90deg, #7c3aed 0%, #a855f7 100%)", "#a855f7", "rgba(168, 85, 247, 0.15)"),
                            ("linear-gradient(90deg, #db2777 0%, #ec4899 100%)", "#ec4899", "rgba(236, 72, 153, 0.15)")
                        ]
                        html_prof_rows = ""
                        for idx, row in prof_counts.iterrows():
                            p_grad, p_col, p_bg = prof_palette[idx % len(prof_palette)]
                            p_name = row["الفئة الاجتماعية"]
                            p_cnt = int(row["عدد المشاركين"])
                            p_pct = float(row["النسبة %"])
                            p_bar_w = max(p_pct, 4.0)
                            html_prof_rows += f"""
                            <div style="margin-bottom: 12px; background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 12px 16px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                                    <span style="font-size: 0.96rem; font-weight: 700; color: #f1f5f9; line-height: 1.5;">👤 {p_name}</span>
                                    <span style="font-size: 0.88rem; font-weight: 800; color: {p_col}; background: {p_bg}; border: 1px solid {p_col}44; padding: 3px 12px; border-radius: 16px; white-space: nowrap;">
                                        {p_cnt} مشارك ({p_pct:.1f}%)
                                    </span>
                                </div>
                                <div style="background: rgba(15, 23, 42, 0.7); border-radius: 8px; height: 12px; width: 100%; overflow: hidden; padding: 1px;">
                                    <div style="background: {p_grad}; width: {p_bar_w}%; height: 100%; border-radius: 6px; box-shadow: 0 0 8px {p_col}55;"></div>
                                </div>
                            </div>
                            """
                        prof_card_html = f"""
                        <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 16px; padding: 18px 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.35); user-select: none;">
                            <div style="font-size: 1.08rem; font-weight: 800; color: #f8fafc; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
                                👥 توزيع المشاركين حسب الفئات الاجتماعية
                            </div>
                            {html_prof_rows}
                        </div>
                        """
                        st.html(prof_card_html)
                    else:
                        st.info("لا توجد بيانات تفصيلية للفئات حالياً.")
                except Exception:
                    st.info("لا توجد بيانات تفصيلية للفئات حالياً.")

# PAGE 2: مخصصات موازنة 2026/2027
elif page == "💰 مخصصات موازنة 2026/2027":
    st.subheader("🏛️ أبرز المخصصات الحيوية بموازنة المواطن 2026/2027")
    st.caption("الاستحقاقات الدستورية ومخصصات التنمية البشرية والحماية الاجتماعية المعتمدة:")

    allocations = [
        {"القطاع": "التعليم والبحث العلمي", "المخصصات (مليار جنيه)": 1229.7, "النسبة من الناتج المحلي": "6.0%", "النمو السنوي": "+17.9%"},
        {"القطاع": "الصحة والخدمات الطبية", "المخصصات (مليار جنيه)": 862.9, "النسبة من الناتج المحلي": "4.2%", "النمو السنوي": "+39.6%"},
        {"القطاع": "الدعم والمنح الاجتماعية", "المخصصات (مليار جنيه)": 836.8, "النسبة من الناتج المحلي": "3.4%", "النمو السنوي": "+12.7%"},
        {"القطاع": "الأجور وتعويضات العاملين", "المخصصات (مليار جنيه)": 822.8, "النسبة من الناتج المحلي": "3.3%", "النمو السنوي": "+21.2%"},
        {"القطاع": "دعم الأنشطة الاقتصادية والإنتاج", "المخصصات (مليار جنيه)": 90.0, "النسبة من الناتج المحلي": "-", "النمو السنوي": "مبادرات جديدة"}
    ]
    df_alloc = pd.DataFrame(allocations)

    # 4 Quick KPI Highlight Cards at the top
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric(label="التعليم والبحث العلمي", value="1,229.7 مليار ج.م", delta="+17.9% استحقاق دستوري")
    with k2:
        st.metric(label="الصحة والتأمين الصحي", value="862.9 مليار ج.م", delta="+39.6% أعلى نمو سنوي")
    with k3:
        st.metric(label="الدعم والمنح الاجتماعية", value="836.8 مليار ج.م", delta="+12.7% حماية اجتماعية")
    with k4:
        st.metric(label="الأجور وتعويضات العاملين", value="822.8 مليار ج.م", delta="+21.2% حزمة تبكير يوليو")

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    sector_styles = [
        {"icon": "📚", "grad": "linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)", "color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.15)"},
        {"icon": "🏥", "grad": "linear-gradient(90deg, #059669 0%, #10b981 100%)", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.15)"},
        {"icon": "🍞", "grad": "linear-gradient(90deg, #d97706 0%, #f59e0b 100%)", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.15)"},
        {"icon": "💼", "grad": "linear-gradient(90deg, #4f46e5 0%, #818cf8 100%)", "color": "#818cf8", "bg": "rgba(129, 140, 248, 0.15)"},
        {"icon": "🏭", "grad": "linear-gradient(90deg, #db2777 0%, #ec4899 100%)", "color": "#ec4899", "bg": "rgba(236, 72, 153, 0.15)"}
    ]
    max_alloc = max(df_alloc["المخصصات (مليار جنيه)"])
    html_alloc_rows = ""
    for idx, row in df_alloc.iterrows():
        style = sector_styles[idx % len(sector_styles)]
        sec_name = row["القطاع"]
        sec_val = float(row["المخصصات (مليار جنيه)"])
        sec_gdp = row["النسبة من الناتج المحلي"]
        sec_growth = row["النمو السنوي"]
        bar_w = (sec_val / max_alloc) * 100
        
        gdp_badge = f"""<span style="font-size: 0.82rem; color: #94a3b8; background: rgba(255,255,255,0.06); padding: 3px 10px; border-radius: 12px; margin-right: 6px;">{sec_gdp} الناتج (GDP)</span>""" if sec_gdp != "-" else ""
        growth_badge = f"""<span style="font-size: 0.82rem; color: #34d399; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); padding: 3px 10px; border-radius: 12px;">{sec_growth}</span>"""

        html_alloc_rows += f"""
        <div style="margin-bottom: 14px; background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                <div style="font-size: 1.02rem; font-weight: 700; color: #f8fafc;">
                    {style['icon']} {sec_name}
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    {gdp_badge}
                    {growth_badge}
                    <span style="font-size: 0.95rem; font-weight: 800; color: {style['color']}; background: {style['bg']}; border: 1px solid {style['color']}44; padding: 3px 12px; border-radius: 16px; white-space: nowrap;">
                        {sec_val:,.1f} مليار ج.م
                    </span>
                </div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.7); border-radius: 8px; height: 14px; width: 100%; overflow: hidden; padding: 1px;">
                <div style="background: {style['grad']}; width: {bar_w}%; height: 100%; border-radius: 6px; box-shadow: 0 0 10px {style['color']}55;"></div>
            </div>
        </div>
        """

    alloc_card_html = f"""
    <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 16px; padding: 20px 22px; box-shadow: 0 8px 25px rgba(0,0,0,0.35); user-select: none; margin-bottom: 20px;">
        <div style="font-size: 1.15rem; font-weight: 800; color: #f8fafc; margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">
            🏛️ توزيع مخصصات القطاعات الحيوية بموازنة المواطن 2026/2027
        </div>
        {html_alloc_rows}
    </div>
    """
    st.html(alloc_card_html)

# PAGE 3: مستكشف الأرقام المؤكدة
elif page == "🔍 مستكشف الأرقام المؤكدة (Facts Ledger)":
    st.subheader("📑 سجل الأرقام المعتمدة (Facts Ledger) — المصدر الموثوق")
    st.caption("كل رقم في هذا السجل تمت مراجعته وتوثيقه نصياً من تقرير موازنة المواطن 2026/2027:")

    facts = grounding_engine.facts
    if facts:
        table_data = []
        for f in facts:
            table_data.append({
                "الموضوع": f.get("topic", ""),
                "البيان": f.get("label_ar", ""),
                "القيمة / المؤشر": f.get("display_ar", ""),
                "المصدر في التقرير": f.get("source", "")
            })
        df_facts = pd.DataFrame(table_data)
        
        search_query = st.text_input("🔎 ابحث في الأرقام المؤكدة (مثال: صحة، أجور، ضرائب، تكافل):")
        if search_query:
            df_facts = df_facts[df_facts.apply(lambda row: search_query.lower() in row.to_string().lower(), axis=1)]
            
        st.dataframe(df_facts, hide_index=True, use_container_width=True, height=500)

# PAGE 4: محاكي المحادثة والتحقق
elif page == "💬 محاكي المحادثة والتحقق (Live Demo)":
    st.subheader("🤖 محاكي تجربة المواطن عبر 'حسبتك'")
    st.caption("اختبار مباشر لمحرك التأصيل (Grounding Layer) وحاجز الأرقام الصارم (Numeric Guardrail):")

    core = HasebtakCore()

    # Accessibility Toggle for Universal Guided Audio-Visual Navigation
    accessible_mode = st.checkbox(
        "🎙️ تفعيل واجهة المساعدة الصوتية والبصرية الميسّرة (Accessible Guided Mode)",
        value=False
    )

    # Dynamic Profiles, Subcategories and Tailored Question Bank
    profile_hierarchy = {
        "مواطن": {
            "مواطن / رب أسرة": [
                "دعم السلع التموينية ورغيف العيش كام السنة دي وهيستفيد منه كام مواطن؟",
                "دعم الكهرباء وفواتير المنازل مخصص له كام في موازنة 2026/2027؟",
                "إيه تفاصيل سند المواطن والعائد الشهري 17.75%؟",
                "حد الإعفاء للسكن الخاص في الضريبة العقارية اترفع لكام؟",
                "كام ميزانية رحلات الفضاء الاستكشافية؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "على المعاش / متقاعد": [
                "الحزم الاجتماعية ومخصصات المعاشات ودعم رمضان في الموازنة كام؟",
                "التأمين الصحي الشامل بيغطي غير القادرين وأصحاب المعاشات إزاي ومخصص له كام؟",
                "إيه مميزات سند المواطن الاستثماري كوعاء ادخاري آمن بعائد شهري؟",
                "مخصصات قرارات العلاج على نفقة الدولة والجراحات الحرجة كام؟",
                "كام معاش رواد الفضاء في الموازنة؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "ربة منزل": [
                "مخصصات برنامج تكافل وكرامة للأسر الأولى بالرعاية كام وأستفيد إزاي؟",
                "دعم السلع التموينية ورغيف العيش وحصة الفرد كام؟",
                "برنامج التغذية المدرسية لصحة الطلاب والأطفال مخصص له كام؟",
                "دعم التأمين الصحي للأطفال دون سن المدرسة كام في الموازنة؟",
                "كام تكلفة شراء يخوت فاخرة في التقرير؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "باحث عن عمل / عمل حر": [
                "معدل البطالة المستهدف وفرص العمل في موازنة 2026/2027 كام؟",
                "برامج الحماية الاجتماعية المتاحة ودعم العمالة غير المنتظمة إيه؟",
                "الحوافز النقدية للمشروعات وتسهيلات بدء نشاط حر كام؟",
                "المنظومة الضريبية المبسطة بتساعد المهن الحرة إزاي؟",
                "كام ميزانية توظيف الفضائيين في الحكومة؟ (سؤال غير موجود لاختبار الأمان)"
            ]
        },
        "موظف": {
            "الجهاز الإداري للدولة (عام)": [
                "الحد الأدنى للأجور للعاملين بالدولة بقى كام في الموازنة الجديدة؟",
                "إجمالي مخصصات الأجور وتكلفة حزمة زيادة يوليو 2026 كام؟",
                "في علاوات دورية أو حوافز إضافية لموظفي الجهاز الإداري؟",
                "إيه مميزات الاستثمار في سند المواطن الشهري للموظفين؟",
                "كام ميزانية بدل السفر لكوكب المشتري؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "قطاع التعليم (معلم / كادر تعليمي)": [
                "في حوافز أو بدلات إضافية لمعلمي ومدرسي المدارس الحكومية؟",
                "مخصصات قطاع التعليم استيفاءً للاستحقاق الدستوري وصلت لكام؟",
                "ميزانية الأجور وحزمة يوليو 2026 هتأثر إزاي على مرتبات المعلمين؟",
                "مخصصات بناء الفصول وتطوير المدارس لتقليل الكثافة كام؟",
                "كام مرتب معلم في مدرسة الفضاء؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "قطاع الصحة (طبيب / كادر طبي)": [
                "مخصصات الصحة في موازنة 2026/2027 كام ونسبتها للناتج المحلي؟",
                "مخصصات هيئة الشراء الموحد للأدوية والمستلزمات الطبية كام؟",
                "في حوافز إضافية للأطباء والتمريض والكوادر الطبية في الموازنة؟",
                "مخصصات العلاج على نفقة الدولة زادت بنسبة كام؟",
                "كام تكلفة استيراد أدوية من المريخ؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "قطاع الإنتاج والخدمات": [
                "تمويل التسهيلات الائتمانية لقطاعات الإنتاج مخصص له كام (6 مليار)؟",
                "الحد الأدنى للأجور وتأثيره على العاملين في قطاعات الدولة؟",
                "حوافز توطين الصناعة والصناعات ذات الأولوية كام؟",
                "التيسيرات الضريبية لبيئة الأعمال والإنتاج إيه تفاصيلها؟",
                "كام ميزانية منجم الألماس في القمر؟ (سؤال غير موجود لاختبار الأمان)"
            ]
        },
        "طالب": {
            "طالب جامعي": [
                "اشتراكات المترو والقطارات للطلبة مدعومة بكام في الموازنة؟",
                "دعم التأمين الصحي للطلاب في الجامعات مخصص له كام؟",
                "مخصصات الجامعات التكنولوجية والتحول الرقمي للتعليم العالي كام؟",
                "في منح أو مسابقات ابتكار ودعم للمشاريع الطلابية في الموازنة؟",
                "كام ميزانية جامعة المجرات للطلاب؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "طالب مدرسي": [
                "ميزانية الوجبات والتغذية المدرسية كام وهتفيد كام طالب؟",
                "دعم التأمين الصحي للتلاميذ والأطفال دون سن المدرسة كام (390 مليون)؟",
                "مخصصات المدارس وتطوير الفصول في قطاع التعليم كام؟",
                "اشتراكات الطلبة في المترو بتوفر كام للأسرة؟",
                "كام سعر الوجبة المدرسية الذهبية؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "دراسات عليا وبحث علمي": [
                "مخصصات قطاع البحث العلمي كام في موازنة 2026/2027 ونسبتها للـ GDP؟",
                "في تمويل للمراكز البحثية والابتكار التكنولوجي في الموازنة؟",
                "مخصصات قطاع التعليم والبحث العلمي استيفاءً للدستور وصلت لكام؟",
                "إيه المجالات والصناعات ذات الأولوية اللي الدولة بتدعم بحوثها؟",
                "كام ميزانية بحوث السفر عبر الزمن؟ (سؤال غير موجود لاختبار الأمان)"
            ]
        },
        "صاحب مشروع": {
            "مشروعات صغيرة ومتوسطة (SME)": [
                "إيه تفاصيل الحوافز النقدية للمشروعات الصغيرة وريادة الأعمال (5 مليار)؟",
                "المنظومة الضريبية المبسطة للمشروعات وضم 100 ألف ممول إيه شروطها؟",
                "إيه هي 'القائمة البيضاء' للممولين الملتزمين ومزاياها للمشروعات؟",
                "تسهيلات تمويل قطاعات الإنتاج بـ 6 مليارات جنيه أستفيد منها إزاي؟",
                "كام حافز تأسيس شركة على سطح القمر؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "رائد أعمال / شركات ناشئة": [
                "حوافز ريادة الأعمال والشركات الناشئة في موازنة 2026/2027 كام؟",
                "تيسيرات الضرائب والإعفاء من رسوم التوثيق والدمغة للمشروعات الناشئة إيه؟",
                "تمويل التسهيلات والابتكار الصناعي والإنتاجي مخصص له كام؟",
                "سند المواطن بعائد 17.75% شهرياً أقدر استثمر فيه فوائض الشركة؟",
                "كام تمويل صندوق العملات المشفرة للمريخ؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "تصدير وصناعات تحويلية": [
                "مخصصات برنامج رد الأعباء التصديرية ودعم المصدرين كام (48 مليار)؟",
                "حوافز توطين صناعة السيارات الكهربائية والصديقة للبيئة كام (5.5 مليار)؟",
                "تسهيلات ائتمان وتمويل قطاعات الإنتاج السلعي والصناعي كام؟",
                "حوافز الصناعات ذات الأولوية الاستراتيجية مخصص لها كام؟",
                "كام دعم صادرات الجليد للقطب الشمالي؟ (سؤال غير موجود لاختبار الأمان)"
            ],
            "أنشطة تجارية ومهن حرة": [
                "المنظومة الضريبية المبسطة بتفيد أصحاب المهن الحرة والتجارة إزاي؟",
                "تخفيض ضريبة القيمة المضافة من 14% إلى 5% على الأجهزة الطبية؟",
                "حد إعفاء السكن الخاص في الضريبة العقارية اترفع لـ 8 ملايين جنيه إزاي؟",
                "إيه هي التيسيرات في الفحص بالعينة وتوفيق الأوضاع للممولين؟",
                "كام ضريبة بيع الهواء في المحلات؟ (سؤال غير موجود لاختبار الأمان)"
            ]
        }
    }

    if accessible_mode:
        st.markdown("""
        <div style="background: #f0fdf4; border: 2px solid #22c55e; padding: 18px; border-radius: 12px; margin-bottom: 20px;">
            <h3 style="color: #15803d; margin: 0 0 6px 0;">🎙️ واجهة المساعدة الصوتية والبصرية الميسّرة</h3>
            <p style="color: #334155; margin: 0; font-size: 1.05rem;">
                اختر المربع الملون المناسب لموضوعك، وسيتم قراءة وشرح الأرقام بالصوت المصري الواضح.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Audio Guide Button
        if st.button("🔊 استمع للإرشاد الصوتي العام (شرح المربعات والألوان)", use_container_width=True):
            guide_text = (
                "أهلاً بيك يا فندم في موازنة بلدك. قدامك أربعة مربعات ملونة بأرقام كبيرة: "
                "المربع الأزرق رقم 1: لمخصصات التعليم والصحة والأجور. "
                "المربع الأخضر رقم 2: لدليل الدعم وتكافل وكرامة. "
                "المربع البرتقالي رقم 3: للمشاركة في استطلاع الأسبوع. "
                "المربع البنفسجي رقم 4: للتيسيرات والمزايا الخاصة. "
                "اضغط على المربع اللي تحبه، وهنشرحلك كل الأرقام بالصوت الواضح."
            )
            try:
                guide_audio = text_to_speech(guide_text)
                if guide_audio and os.path.exists(guide_audio):
                    with open(guide_audio, "rb") as f:
                        st.audio(f.read(), format="audio/mp3")
            except Exception:
                pass

        # 4 Large Colored Cards in 2 Columns
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown("""
            <div class="accessible-box box-blue">
                <div style="font-size: 1.6rem; margin-bottom: 4px;">🟦 المربع رقم [ 1 ]</div>
                <div>🏛️ اسأل عن مخصصات الموازنة العامة</div>
                <div style="font-size: 0.95rem; font-weight: 400; opacity: 0.9; margin-top: 4px;">(التعليم 📚 • الصحة 🏥 • الأجور والمرتبات 💼)</div>
            </div>
            """, unsafe_allow_html=True)
            sel_box1 = st.button("👉 فتح خيارات المربع الأزرق [1]", key="acc_btn_1", use_container_width=True)

        with col_c2:
            st.markdown("""
            <div class="accessible-box box-green">
                <div style="font-size: 1.6rem; margin-bottom: 4px;">🟩 المربع رقم [ 2 ]</div>
                <div>🤝 هل تستحق الدعم وتكافل وكرامة؟</div>
                <div style="font-size: 0.95rem; font-weight: 400; opacity: 0.9; margin-top: 4px;">(تكافل وكرامة • بطاقة التموين • التأمين الصحي)</div>
            </div>
            """, unsafe_allow_html=True)
            sel_box2 = st.button("👉 فتح خيارات المربع الأخضر [2]", key="acc_btn_2", use_container_width=True)

        col_c3, col_c4 = st.columns(2)
        with col_c3:
            st.markdown("""
            <div class="accessible-box box-orange">
                <div style="font-size: 1.6rem; margin-bottom: 4px;">🟧 المربع رقم [ 3 ]</div>
                <div>🗳️ نبض المواطن واستطلاع الأسبوع</div>
                <div style="font-size: 0.95rem; font-weight: 400; opacity: 0.9; margin-top: 4px;">(شارك برأيك المباشر لوزارة المالية)</div>
            </div>
            """, unsafe_allow_html=True)
            sel_box3 = st.button("👉 فتح خيارات المربع البرتقالي [3]", key="acc_btn_3", use_container_width=True)

        with col_c4:
            st.markdown("""
            <div class="accessible-box box-purple">
                <div style="font-size: 1.6rem; margin-bottom: 4px;">🟪 المربع رقم [ 4 ]</div>
                <div>🧓 التيسيرات والمزايا الخاصة</div>
                <div style="font-size: 0.95rem; font-weight: 400; opacity: 0.9; margin-top: 4px;">(كبار السن والمعاشات • ذوي الهمم • سند المواطن)</div>
            </div>
            """, unsafe_allow_html=True)
            sel_box4 = st.button("👉 فتح خيارات المربع البنفسجي [4]", key="acc_btn_4", use_container_width=True)

        if "acc_section" not in st.session_state:
            st.session_state.acc_section = "box1"

        if sel_box1: st.session_state.acc_section = "box1"
        if sel_box2: st.session_state.acc_section = "box2"
        if sel_box3: st.session_state.acc_section = "box3"
        if sel_box4: st.session_state.acc_section = "box4"

        active_sec = st.session_state.acc_section
        active_q = None

        st.markdown("---")
        if active_sec == "box1":
            st.subheader("🟦 خيارات المربع الأزرق [1]: مخصصات الموازنة العامة")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                if st.button("📚 مخصصات التعليم والمدارس", key="acc_q_edu", use_container_width=True):
                    active_q = "مخصصات قطاع التعليم كام في موازنة 2026/2027 وليه زادت؟"
            with col_q2:
                if st.button("🏥 مخصصات الصحة والمستشفيات", key="acc_q_health", use_container_width=True):
                    active_q = "مخصصات الصحة في موازنة 2026/2027 كام والتأمين الصحي؟"
            with col_q3:
                if st.button("💼 مخصصات الأجور وحزمة يوليو", key="acc_q_wages", use_container_width=True):
                    active_q = "إجمالي مخصصات الأجور وتكلفة حزمة زيادة يوليو 2026 كام؟"

        elif active_sec == "box2":
            st.subheader("🟩 خيارات المربع الأخضر [2]: هل تستحق الدعم؟")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                if st.button("🤝 دعم تكافل وكرامة", key="acc_q_tak", use_container_width=True):
                    active_q = "إيه هي شروط استحقاق معاش تكافل وكرامة وأقدم إزاي؟"
            with col_q2:
                if st.button("🍞 دعم التموين ورغيف العيش", key="acc_q_rat", use_container_width=True):
                    active_q = "دعم السلع التموينية ورغيف العيش كام السنة دي؟"
            with col_q3:
                if st.button("🩺 التأمين الصحي لغير القادرين", key="acc_q_hins", use_container_width=True):
                    active_q = "إزاي غير القادرين بيستفيدوا من التأمين الصحي الشامل؟"

        elif active_sec == "box3":
            st.subheader("🟧 خيارات المربع البرتقالي [3]: نبض المواطن واستطلاع الأسبوع")
            active_poll = poll_engine.get_active_poll()
            if active_poll:
                st.info(f"📋 **سؤال الاستطلاع النشط:** {active_poll['question_ar']}")
                col_opts = st.columns(len(active_poll["options"]))
                for idx, opt in enumerate(active_poll["options"]):
                    with col_opts[idx]:
                        if st.button(f"🔘 {opt['text_ar']}", key=f"acc_vote_{opt['id']}", use_container_width=True):
                            if "poll_user_id" not in st.session_state:
                                import uuid
                                st.session_state.poll_user_id = f"web_{uuid.uuid4().hex[:10]}"
                            vote_res = poll_engine.record_vote(st.session_state.poll_user_id, active_poll["id"], opt["id"], "مواطن")
                            reply_msg = vote_res.get("message") or vote_res.get("reply") or "تم تسجيل مشاركتك بنجاح!"
                            st.success(reply_msg)
                            try:
                                v_audio = text_to_speech(reply_msg)
                                if v_audio and os.path.exists(v_audio):
                                    with open(v_audio, "rb") as f:
                                        st.audio(f.read(), format="audio/mp3")
                            except Exception:
                                pass

        elif active_sec == "box4":
            st.subheader("🟪 خيارات المربع البنفسجي [4]: التيسيرات والمزايا الخاصة")
            col_q1, col_q2, col_q3 = st.columns(3)
            with col_q1:
                if st.button("🧓 مزايا أصحاب المعاشات", key="acc_q_pens", use_container_width=True):
                    active_q = "الحزم الاجتماعية ومخصصات المعاشات في الموازنة كام؟"
            with col_q2:
                if st.button("♿ إعفاءات وتيسيرات ذوي الهمم", key="acc_q_dis", use_container_width=True):
                    active_q = "إيه التيسيرات والإعفاءات المخصصة لذوي الهمم في الموازنة؟"
            with col_q3:
                if st.button("📈 سند المواطن 17.75% شهرياً", key="acc_q_bond", use_container_width=True):
                    active_q = "إيه تفاصيل ومميزات سند المواطن بعائد شهري 17.75%؟"

        custom_q_acc = st.text_input("أو اكتب أي سؤال هنا:", placeholder="مثال: مخصصات التعليم كام؟")
        if st.button("🚀 استشر حسبتك بالصوت والنص", key="acc_submit"):
            if custom_q_acc:
                active_q = custom_q_acc

        if active_q:
            with st.spinner("جاري استرجاع الأرقام المؤكدة وقراءة الإجابة صوتياً... 🎙️"):
                res_acc = core.answer_budget_question(active_q, user_profile="مواطن")
                st.markdown("### 💬 إجابة حسبتك للمواطن:")
                st.success(res_acc["reply"])
                try:
                    ans_audio = text_to_speech(res_acc["reply"])
                    if ans_audio and os.path.exists(ans_audio):
                        st.markdown("#### 🔊 استمع للإجابة بالصوت المصري:")
                        with open(ans_audio, "rb") as f:
                            st.audio(f.read(), format="audio/mp3")
                except Exception:
                    pass

    else:
        # Standard Selection Layout: Main Profile & Subcategory
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            main_profile = st.selectbox(
                "👤 اختر فئة المواطن الرئيسية:",
                list(profile_hierarchy.keys()),
                help="حدد الفئة الأساسية لتخصيص نتائج الموازنة بما يهمك."
            )

        subcategories = list(profile_hierarchy[main_profile].keys())
        with col_p2:
            sub_label = {
                "مواطن": "🏷️ تحديد الحالة والنشاط:",
                "موظف": "🏢 تحديد قطاع العمل:",
                "طالب": "🎓 تحديد المرحلة التعليمية:",
                "صاحب مشروع": "💼 طبيعة النشاط وحجم المشروع:"
            }.get(main_profile, "🏷️ التصنيف الفرعي:")

            sub_profile = st.selectbox(
                sub_label,
                subcategories,
                help="تصنيف فرعي دقيق لعرض الأسئلة والحوافز الأكثر ارتباطاً بك."
            )

        # Composite Profile representation
        user_profile_combined = f"{main_profile} ({sub_profile})"

        # Display active badge
        st.info(f"🎯 **الملف النشط المخصص للإجابة:** `{user_profile_combined}`")

        # Tailored Sample Questions
        tailored_questions = profile_hierarchy[main_profile][sub_profile]
        selected_sample = st.selectbox(
            f"💡 اختر سؤالاً مقترحاً لـ [{sub_profile}]:",
            [""] + tailored_questions
        )
        
        user_q = st.text_input("أو اكتب سؤالك الخاص هنا:", value=selected_sample)

        col_btn, col_voice = st.columns([1, 2])
        with col_btn:
            submit_clicked = st.button("🚀 إرسال واستشارة حسبتك")
        with col_voice:
            play_voice = st.checkbox("🔊 سماع الرد صوتياً (بالعامية المصرية)", value=False)

        if submit_clicked and user_q:
            with st.spinner("جاري استرجاع الأرقام المؤكدة وتطبيق حاجز الأمان..."):
                res = core.answer_budget_question(user_q, user_profile=user_profile_combined)
                
                st.markdown("### 💬 إجابة حسبتك للمواطن:")
                st.success(res["reply"])

                if play_voice and res.get("reply"):
                    try:
                        audio_path = text_to_speech(res["reply"])
                        if audio_path and os.path.exists(audio_path):
                            with open(audio_path, "rb") as f:
                                st.audio(f.read(), format="audio/mp3")
                    except Exception as e:
                        pass

                with st.expander("🛡️ تفاصيل التأصيل وحاجز الأمان (Grounding & Guardrail Audit)"):
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.write("**حالة حاجز الأمان الرياضي:**", "✅ معتمد (Grounded)" if res["guardrail_passed"] else "❌ تم الحجب")
                    with col_g2:
                        st.write("**المصادر المعتمدة المرجعية:**", res.get("sources", []))

                    if res.get("blocked_numbers"):
                        st.error(f"أرقام تم حجبها لعدم وجودها في التقرير الرسمي: {res['blocked_numbers']}")
