"""
dashboard.py
Streamlit dashboard for the municipal grant announcement tracker.
Reads directly from announcements.db on every load — automatically
reflects new data once the daily Airflow scraper is running.

Run with: streamlit run dashboard.py
"""

import json
import re
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from rapidfuzz import fuzz

# ─────────────────────────────────────────────────────────────
#  DARK THEME + CUSTOM CSS (injected before anything else)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="متتبع المشاريع - بلدية تاجنانت -",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Municipal Grant Tracker — built with Streamlit"}
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+Arabic:wght@300;400;500;600;700&display=swap');

/* ── Root overrides ── */
:root {
    --bg-deep: #0B0E14;
    --bg-surface: #111827;
    --bg-elevated: #1A2234;
    --bg-card: #1E293B;
    --border: #2D3A4F;
    --text-primary: #E2E8F0;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent: #38BDF8;
    --accent-soft: #0EA5E9;
    --accent-glow: rgba(56, 189, 248, 0.15);
    --danger: #F87171;
    --success: #34D399;
    --warning: #FBBF24;
    --radius: 12px;
    --radius-sm: 8px;
}

/* ── Hide Streamlit chrome ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── Global background ── */
.stApp {
    background: var(--bg-deep) !important;
    font-family: 'Inter', 'Noto Sans Arabic', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-deep) 100%) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 1rem !important;
}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-primary) !important;
    text-align: right !important;
    direction: rtl !important;
}
h1 {
    font-weight: 800 !important;
    font-size: 2.2rem !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 0.25rem !important;
}
.stCaption {
    color: var(--text-muted) !important;
    font-size: 0.9rem !important;
    text-align: right !important;
    direction: rtl !important;
}

/* ── Right-align all Streamlit text containers ── */
.stMarkdown, .stText, p, div[data-testid="stMarkdownContainer"] {
    text-align: right !important;
    direction: rtl !important;
}

/* ── Right-align subheaders specifically ── */
[data-testid="stSubheader"] {
    text-align: right !important;
    direction: rtl !important;
    justify-content: flex-end !important;
}

/* ── Metric labels right-aligned ── */
[data-testid="stMetric"] {
    text-align: right !important;
    direction: rtl !important;
}
[data-testid="stMetric"] label {
    text-align: right !important;
    direction: rtl !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 4px !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 0 !important;
    display: flex !important;
    flex-direction: row-reverse !important;
    justify-content: flex-start !important;
    overflow-x: auto !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background: rgba(255,255,255,0.03) !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    background: var(--accent-glow) !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1.2rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    min-width: 0 !important;
    overflow: visible !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4) !important;
    border-color: var(--accent) !important;
}
[data-testid="stMetric"] > div {
    min-width: 0 !important;
    overflow: visible !important;
}
[data-testid="stMetric"] label {
    color: var(--text-muted) !important;
    font-size: 0.65rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    text-align: right !important;
    direction: rtl !important;
    white-space: nowrap !important;
    line-height: 1.2 !important;
}
[data-testid="stMetric"] .stMetricValue {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    text-align: right !important;
    direction: ltr !important; 
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

/* 👈 Wildcard to kill Streamlit's hidden ellipsis rules */
[data-testid="stMetric"] * {
    overflow: visible !important;
    text-overflow: clip !important;
}

[data-testid="stMetric"] .stMetricValue > div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

[data-testid="stMetric"] .stMetricDelta {
    color: var(--text-secondary) !important;
    font-size: 0.8rem !important;
}

/* ── Dataframes / Tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    border-bottom: 1px solid var(--border) !important;
}
[data-testid="stDataFrame"] td {
    background: var(--bg-card) !important;
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    border-bottom: 1px solid rgba(45, 58, 79, 0.5) !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
}

/* ── Buttons ── */
.stButton>button {
    background: linear-gradient(135deg, var(--accent-soft), var(--accent)) !important;
    color: #0B0E14 !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.2rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(56, 189, 248, 0.2) !important;
}
.stButton>button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(56, 189, 248, 0.35) !important;
}
.stButton>button:active {
    transform: translateY(0) !important;
}

/* ── Sliders / Inputs ── */
[data-testid="stSlider"] {
    color: var(--accent) !important;
}
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-elevated) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
}
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] > div > div:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

/* ── Multiselect / Radio ── */
[data-testid="stMultiSelect"] span,
[data-testid="stRadio"] label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
}
[data-testid="stRadio"] [role="radiogroup"] label[data-baseweb="radio"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    padding: 0.4rem 0.8rem !important;
    margin-right: 0.5rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stExpander"] > div:first-child {
    color: var(--text-primary) !important;
    font-weight: 500 !important;
}

/* ── Divider ── */
hr {
    border-color: var(--border) !important;
    opacity: 0.5 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bg-deep); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* ── Plotly charts dark background fix ── */
.js-plotly-plot .plotly .main-svg {
    background: transparent !important;
}

/* ── Glow accent line under header ── */
.header-glow {
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    margin: 0.5rem 0 1.5rem 0;
    border-radius: 1px;
    opacity: 0.6;
}

/* ── Card wrapper for sections ── */
.glass-card {
    background: rgba(30, 41, 59, 0.6) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(45, 58, 79, 0.8) !important;
    border-radius: var(--radius) !important;
    padding: 1.5rem !important;
}

/* ── Toggle / Checkbox ── */
[data-testid="stCheckbox"] label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
}

/* ── Center the main content area ── */
.block-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding-top: 2rem !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
DB_PATH = "announcements.db"
OVERRIDES_FILE = "manual_group_overrides.json"

ARABIC_MONTHS = {
    "جانفي": 1, "فيفري": 2, "فبراير": 2, "مارس": 3,
    "أفريل": 4, "افريل": 4, "أبريل": 4,
    "ماي": 5, "جوان": 6, "جويلية": 7, "جويليه": 7, "أوت": 8, "اوت": 8,
    "سبتمبر": 9, "أكتوبر": 10, "اكتوبر": 10, "نوفمبر": 11,
    "ديسمبر": 12, "ديسـمبر": 12,
}

EXCLUDED_PROJECT_KEYWORD = "النقل المدرسي"
FUZZY_GROUP_THRESHOLD = 85

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def normalize_amount(amount_str):
    if not amount_str:
        return None
    s = str(amount_str)
    s = s.replace("دج", "").strip()
    s = s.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_messy_date(date_str):
    if not date_str:
        return pd.NaT
    s = str(date_str).strip()

    # First: try Arabic month names
    for month_name, month_num in ARABIC_MONTHS.items():
        if month_name in s:
            match = re.search(r"(\d{1,2}).*?(\d{4})", s)
            if match:
                day, year = match.groups()
                try:
                    return pd.Timestamp(year=int(year), month=month_num, day=int(day))
                except ValueError:
                    return pd.NaT

    # Second: explicit YYYY/MM/DD or YYYY-MM-DD formats (year first)
    # These must be parsed as-is; dayfirst=True would corrupt them
    year_first = re.match(r"(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})", s)
    if year_first:
        year, month, day = year_first.groups()
        try:
            return pd.Timestamp(year=int(year), month=int(month), day=int(day))
        except ValueError:
            return pd.NaT

    # Third: year-only strings (e.g. "2026", "2026 ") — leave unparsed
    if re.fullmatch(r"\d{4}", s):
        return pd.NaT

    # Fallback: ambiguous formats — assume dayfirst (DD/MM/YYYY)
    return pd.to_datetime(s, errors="coerce", dayfirst=True)


def canonicalize_values(values, threshold=FUZZY_GROUP_THRESHOLD):
    canonical_list = []
    mapping = {}
    for v in values:
        if v is None or v == "":
            mapping[v] = v
            continue
        matched = None
        for canon in canonical_list:
            if fuzz.ratio(v, canon) >= threshold:
                matched = canon
                break
        if matched:
            mapping[v] = matched
        else:
            canonical_list.append(v)
            mapping[v] = v
    return mapping


def load_overrides():
    try:
        with open(OVERRIDES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"company": {}, "commune": {}}


def save_overrides(overrides):
    with open(OVERRIDES_FILE, "w", encoding="utf-8") as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)


def apply_overrides(auto_map, override_dict):
    final_map = dict(auto_map)
    for original, forced_target in override_dict.items():
        if original in final_map:
            final_map[original] = forced_target
    return final_map


@st.cache_data(ttl=300)
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM announcements", conn)
    conn.close()

    df = df[~df["project_title"].str.contains(EXCLUDED_PROJECT_KEYWORD, na=False)].copy()

    df["amount_numeric"] = df["amount_in_dinars"].apply(normalize_amount)
    df["date_parsed"] = df["date"].apply(parse_messy_date)

    overrides = load_overrides()

    company_map = canonicalize_values(df["company_name"].dropna().unique())
    company_map = apply_overrides(company_map, overrides.get("company", {}))
    df["company_clean"] = df["company_name"].map(company_map).fillna(df["company_name"])

    commune_map = canonicalize_values(df["commune"].dropna().unique())
    commune_map = apply_overrides(commune_map, overrides.get("commune", {}))
    df["commune_clean"] = df["commune"].map(commune_map).fillna(df["commune"])

    return df


df = load_data()

# ─────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────
st.title("متتبع المشاريع - بلدية تاجنانت -")
st.caption("البيانات مستخرجة من منشورات عمومية على الصفحة الرسمية لبلدية تاجنانت على الفيسبوك. تُحدَّث تلقائيًا عندما تضيف الصفحة منشورات جديدة.")
st.markdown('<div class="header-glow"></div>', unsafe_allow_html=True)

if df.empty:
    st.warning("لم يُعثر على بيانات في announcements.db بعد.")
    st.stop()

# ─────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────
tab_about, tab_overview, tab_companies, tab_explorer, tab_groups = st.tabs(
    ["نبذة عن المشروع", "نظرة عامة", "الشركات", "استكشف أكثر", "مجموعة اسماء الشركات"]
)

# ─────────────────────────────────────────────────────────────
#  SIDEBAR FILTERS
# ─────────────────────────────────────────────────────────────
st.sidebar.header("الفلاتر")

status_options = ["منجز", "ملغى"]
selected_status_labels = st.sidebar.multiselect("الحالة", options=status_options, default=status_options)

valid_dates = df["date_parsed"].dropna()
if not valid_dates.empty:
    min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
    date_range = st.sidebar.date_input("الفترة الزمنية", value=(min_date, max_date))
else:
    date_range = None

filtered = df.copy()

status_mask = pd.Series(False, index=filtered.index)
if "منجز" in selected_status_labels:
    status_mask |= (filtered["cancelled"] == 0)
if "ملغى" in selected_status_labels:
    status_mask |= (filtered["cancelled"] == 1)
filtered = filtered[status_mask]

if date_range and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[
        filtered["date_parsed"].isna()
        | ((filtered["date_parsed"].dt.date >= start) & (filtered["date_parsed"].dt.date <= end))
    ]

# ─────────────────────────────────────────────────────────────
#  PLOTLY THEME OVERRIDE (dark charts)
# ─────────────────────────────────────────────────────────────
PLOTLY_DARK = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, Noto Sans Arabic, sans-serif", color="#E2E8F0"),
    xaxis=dict(gridcolor="rgba(45,58,79,0.3)", zerolinecolor="rgba(45,58,79,0.3)"),
    yaxis=dict(gridcolor="rgba(45,58,79,0.3)", zerolinecolor="rgba(45,58,79,0.3)"),
    legend=dict(bgcolor="rgba(17,24,39,0.8)", bordercolor="rgba(45,58,79,0.5)", borderwidth=1),
    margin=dict(l=40, r=20, t=40, b=40),
)


def apply_dark(fig):
    fig.update_layout(**PLOTLY_DARK)
    return fig

# ─────────────────────────────────────────────────────────────
#  TAB: OVERVIEW
# ─────────────────────────────────────────────────────────────
with tab_about:
    st.markdown("""
    <style>
    .rtl-box {
        direction: rtl;
        text-align: right;
        font-family: 'Noto Sans Arabic', 'Segoe UI', Tahoma, Arial, sans-serif;
        line-height: 2;
        font-size: 16px;
        color: #E2E8F0;
    }
    .rtl-box h2 { text-align: right; direction: rtl; margin-bottom: 20px; color: #38BDF8; }
    .rtl-box h4 { text-align: right; direction: rtl; margin-top: 25px; margin-bottom: 10px; color: #94A3B8; }
    .rtl-box ul { padding-right: 20px; padding-left: 0; margin: 0; }
    .rtl-box li { margin-bottom: 14px; }
    .rtl-box b { color: #E2E8F0; }
    </style>

    <div class="rtl-box">
    <h2>حول هذه اللوحة</h2>

    <p>
    تعرض هذه اللوحة بيانات مستخرجة من منشورات عمومية على الصفحة الرسمية لبلدية تاجنانت على فيسبوك، تتعلق
    بـ "إعلانات المنح المؤقت" و"إعلانات إلغاء المنح المؤقت". يتم تحليل كل صورة
    إعلان باستخدام نموذج ذكاء اصطناعي لاستخراج البيانات المنظمة منها (الشركة،
    المبلغ، المشروع، التاريخ...)، ثم تُخزَّن هذه البيانات وتُربط الإعلانات
    الملغاة بإعلانات المنح الأصلية.
    </p>

    <h4>ملاحظات مهمة حول جودة البيانات</h4>
    <ul>
        <li>
            <b>مشاريع النقل المدرسي مستبعدة بالكامل من هذه اللوحة:</b>
            البيانات المستخرجة من هذه المنح لم تكن كاملة.
            لتفادي عرض بيانات ناقصة أو مضللة، تم استبعاد جميع مشاريع النقل
            المدرسي من كل الرسوم البيانية والجداول في هذه اللوحة.
        </li>
        <li>
            <b>تم تحليل المنشورات المكتوبة باللغة العربية فقط:</b>
            قد تكون هناك منشورات قليلة جداباللغة الفرنسية
            على نفس الصفحة لم يتم اكتشافها أو تحليلها، لأن آلية التصنيف
            تعتمد على عنوان الإعلان باللغة العربية.
        </li>
        <li>
            <b>قد تحتوي بعض الحقول النصية على أخطاء إملائية أو اختلافات طفيفة:</b>
            (اسم الشركة، اسم البلدية، عنوان المشروع) ناتجة عن عملية الاستخراج
            الآلي. تم تجميع الأسماء المتشابهة تلقائيًا لتقليل هذا التأثير،
            ويمكن تصحيح أي تجميع خاطئ يدويًا من تبويب "مجموعة اسماء الشركات".
        </li>
        <li>
            <b>تم استخراج التواريخ من صيغ مختلفة</b> (أشهر بالعربية، صيغ رقمية)
            وتحليلها تلقائيًا؛ قد يفشل تحليل عدد قليل منها فتُستبعد من الرسوم
            الزمنية فقط (تبقى ظاهرة في الجدول التفصيلي).
        </li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
with tab_overview:
    st.subheader("نظرة عامة")

    total_awards = len(filtered)
    total_spend = filtered.loc[filtered["cancelled"] == 0, "amount_numeric"].sum()
    cancelled_df = filtered[filtered["cancelled"] == 1]
    cancelled_count = len(cancelled_df)
    cancellation_rate = (cancelled_count / total_awards * 100) if total_awards else 0
    unique_companies = filtered["company_clean"].nunique()

    # Format large spend numbers compactly
    if total_spend >= 1_000_000_000:
        spend_display = f"{total_spend/1_000_000_000:.2f} مليار دج"
    elif total_spend >= 1_000_000:
        spend_display = f"{total_spend/1_000_000:.1f} مليون دج"
    else:
        spend_display = f"{total_spend:,.0f} دج"

    # Row 1: 2 wider columns for big numbers
    col1, col2 = st.columns(2)
    col1.metric("إجمالي الإعلانات", f"{total_awards:,}")
    col2.metric("إجمالي الإنفاق ", spend_display)

    # Row 2: 2 columns for smaller metrics
    col3, col4 = st.columns(2)
    col3.metric("المشاريع الملغاة", f"{cancelled_count} ({cancellation_rate:.0f}%)")
    col4.metric("عدد الشركات", unique_companies)

    st.divider()

    st.subheader("الإنفاق عبر الزمن")
    time_df = filtered.dropna(subset=["date_parsed"]).copy()
    if not time_df.empty:
        time_df["month"] = time_df["date_parsed"].dt.to_period("M").dt.to_timestamp()
        monthly = (
            time_df[time_df["cancelled"] == 0]
            .groupby("month")["amount_numeric"]
            .sum()
            .reset_index()
        )
        # Format month as string so Plotly treats x-axis as categorical, not datetime
        monthly["month_str"] = monthly["month"].dt.strftime("%Y-%m")
        fig = px.bar(
            monthly, x="month_str", y="amount_numeric",
            labels={"amount_numeric": "الإنفاق (دج)", "month_str": ""},
            color_discrete_sequence=["#38BDF8"],
        )
        fig = apply_dark(fig)
        fig.update_traces(marker_line_width=0, opacity=0.9)
        fig.update_layout(xaxis_type="category")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("لا توجد تواريخ قابلة للتحليل في الفلتر الحالي.")

    st.divider()

    st.subheader("الإلغاءات")
    if cancelled_count > 0:
        with_reason = cancelled_df["cancellation_reason"].notna().sum()
        without_reason = cancelled_count - with_reason

        m1, m2 = st.columns(2)
        m1.metric("ملغاة - مع سبب", with_reason)
        m2.metric("ملغاة - بدون سبب", without_reason)

        reason_split = pd.DataFrame({
            "النوع": ["السبب مذكور", "السبب غير مذكور"],
            "العدد": [with_reason, without_reason],
        })
        fig_reason = px.pie(
            reason_split, names="النوع", values="العدد", hole=0.55,
            color_discrete_sequence=["#F87171", "#FBBF24"],
        )
        fig_reason = apply_dark(fig_reason)
        st.plotly_chart(fig_reason, use_container_width=True)
    else:
        st.info("لا توجد مشاريع ملغاة في الفلتر الحالي.")

# ─────────────────────────────────────────────────────────────
#  TAB: COMPANIES
# ─────────────────────────────────────────────────────────────
with tab_companies:
    st.subheader("أفضل الشركات")
    st.caption("يتم تجميع أسماء الشركات المتشابهة تلقائيًا لتصحيح الأخطاء الإملائية والتكرارات.")

    top_n = st.slider("عرض أفضل N شركة", 5, 30, 10)

    st.markdown("**حسب إجمالي القيمة الممنوحة**")
    by_amount = (
        filtered[filtered["cancelled"] == 0]
        .groupby("company_clean")["amount_numeric"]
        .sum()
        .reset_index()
        .sort_values("amount_numeric", ascending=False)
        .head(top_n)
    )
    fig_amount = px.bar(
        by_amount, x="amount_numeric", y="company_clean", orientation="h",
        labels={"amount_numeric": "المبلغ الاجمالي (دج)", "company_clean": ""},
        color_discrete_sequence=["#34D399"],
    )
    fig_amount = apply_dark(fig_amount)
    fig_amount.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_amount, use_container_width=True)

    st.divider()

    st.markdown("**حسب عدد المشاريع المُنجزة**")
    by_count = (
        filtered.groupby("company_clean")
        .size()
        .reset_index(name="project_count")
        .sort_values("project_count", ascending=False)
        .head(top_n)
    )
    fig_count = px.bar(
        by_count, x="project_count", y="company_clean", orientation="h",
        labels={"project_count": "عدد المشاريع", "company_clean": ""},
        color_discrete_sequence=["#A78BFA"],
    )
    fig_count = apply_dark(fig_count)
    fig_count.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_count, use_container_width=True)

# ─────────────────────────────────────────────────────────────
#  TAB: EXPLORER  (FIXED DATE SORTING)
# ─────────────────────────────────────────────────────────────
with tab_explorer:
    st.subheader("جميع الإعلانات")
    search = st.text_input("ابحث عن شركة أو مشروع")
    display_df = filtered.copy()
    if search:
        mask = (
            display_df["company_clean"].str.contains(search, case=False, na=False)
            | display_df["project_title"].str.contains(search, case=False, na=False)
        )
        display_df = display_df[mask]

    # ── Sort by original DB order (id), not by date ──
    display_sorted = display_df.sort_values("id", ascending=True)

    # Format date: if parsed successfully, show YYYY-MM-DD; otherwise keep raw string
    display_sorted["date_display"] = display_sorted["date_parsed"].dt.strftime("%Y-%m-%d")
    display_sorted["date_display"] = display_sorted["date_display"].fillna(display_sorted["date"])

    st.dataframe(
        display_sorted[[
            "id", "date_display", "company_clean", "amount_in_dinars", "project_title",
            "commune_clean", "cancelled", "cancellation_reason", "source_link",
        ]].rename(columns={"date_display": "date"}),
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", format="%d"),
            "date": st.column_config.TextColumn("التاريخ"),
            "company_clean": st.column_config.TextColumn("الشركة"),
            "amount_in_dinars": st.column_config.TextColumn("المبلغ (دج)"),
            "project_title": st.column_config.TextColumn("المشروع"),
            "commune_clean": st.column_config.TextColumn("البلدية"),
            "cancelled": st.column_config.CheckboxColumn("ملغى"),
            "cancellation_reason": st.column_config.TextColumn("سبب الإلغاء"),
            "source_link": st.column_config.LinkColumn("المصدر"),
        },
        hide_index=True,
    )

    st.divider()

    # ═══════════════════════════════════════════════════════════
    #  BUILD YOUR OWN CHART — ENHANCED WITH MORE FILTERS
    # ═══════════════════════════════════════════════════════════
    st.subheader("ابنِ رسمك البياني")
    st.caption("اختر الأعمدة ونوع الرسم البياني لاستكشاف البيانات بطريقتك.")

    plottable_columns = {
        "Date (month)": "month_bucket",
        "الشركة": "company_clean",
        "البلدية": "commune_clean",
        "Cancelled status": "cancelled",
        "المبلغ (دج)": "amount_numeric",
    }

    plot_df = filtered.copy()
    plot_df["month_bucket"] = plot_df["date_parsed"].dt.to_period("M").dt.to_timestamp()
    plot_df["cancelled"] = plot_df["cancelled"].map({0: "Active", 1: "ملغى"})

    # ── Company filter ──
    all_companies = sorted(plot_df["company_clean"].dropna().unique().tolist())
    selected_companies = st.multiselect(
        "فلتر حسب الشركة",
        options=all_companies,
        default=[],
        placeholder="جميع الشركات محددة",
    )
    if selected_companies:
        plot_df = plot_df[plot_df["company_clean"].isin(selected_companies)]

    # ── Commune filter ──
    all_communes = sorted(plot_df["commune_clean"].dropna().unique().tolist())
    selected_communes = st.multiselect(
        "فلتر حسب البلدية",
        options=all_communes,
        default=[],
        placeholder="جميع البلديات محددة",
    )
    if selected_communes:
        plot_df = plot_df[plot_df["commune_clean"].isin(selected_communes)]

    # ── Status filter (chart-specific, independent of sidebar) ──
    selected_chart_status = st.multiselect(
        "فلتر حسب الحالة",
        options=["Active", "ملغى"],
        default=["Active", "ملغى"],
    )
    plot_df = plot_df[plot_df["cancelled"].isin(selected_chart_status)]

    # ── Amount filter ──
    valid_amounts = plot_df["amount_numeric"].dropna()
    if not valid_amounts.empty:
        amt_min, amt_max = float(valid_amounts.min()), float(valid_amounts.max())
        st.markdown("**فلتر حسب المبلغ (دج)**")
        st.caption("يتم استبعاد الصفوف ذات المبلغ غير المعروف/غير القابل للتحليل عند تطبيق هذا الفلتر.")
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            min_selected = st.number_input("الحد الأدنى", min_value=amt_min, max_value=amt_max, value=amt_min, step=10000.0)
        with fcol2:
            max_selected = st.number_input("الحد الأقصى", min_value=amt_min, max_value=amt_max, value=amt_max, step=10000.0)
        plot_df = plot_df[
            (plot_df["amount_numeric"] >= min_selected) & (plot_df["amount_numeric"] <= max_selected)
        ]

    c1, c2, c3 = st.columns(3)
    with c1:
        x_label = st.selectbox("محور x", list(plottable_columns.keys()), index=0)
    with c2:
        y_label = st.selectbox("محور y", ["Count"] + list(plottable_columns.keys()), index=0)
    with c3:
        chart_type = st.selectbox("نوع الرسم", ["Bar", "Line", "Scatter", "Pie"])

    x_col = plottable_columns[x_label]

    if y_label == "Count":
        chart_data = plot_df.groupby(x_col).size().reset_index(name="Count")
        y_col = "Count"
    else:
        y_col = plottable_columns[y_label]
        if y_col == "amount_numeric":
            chart_data = plot_df.groupby(x_col)[y_col].sum().reset_index()
        else:
            chart_data = plot_df.groupby(x_col).size().reset_index(name="Count")
            y_col = "Count"

    # ═══════════════════════════════════════════════════════════
    #  NEW: "Tag/Keyword grouping" for Pie charts
    #  Groups all items matching a keyword into one slice vs Others
    # ═══════════════════════════════════════════════════════════
    tag_keyword = ""
    group_by_tag = False
    if chart_type == "Pie" and x_col in ("company_clean", "commune_clean"):
        st.markdown("**تجميع حسب الوسم (بحث بالكلمة المفتاحية)**")
        st.caption("اكتب كلمة مفتاحية (مثل 'سطيف') لتجميع جميع العناصر المطابقة في شريحة واحدة. الباقي يصبح 'أخرى'.")
        tag_col1, tag_col2 = st.columns([3, 1])
        with tag_col1:
            tag_keyword = st.text_input(
                "الكلمة المفتاحية للتجميع",
                value="",
                placeholder="مثال: سطيف",
                key="tag_keyword_input",
            )
        with tag_col2:
            group_by_tag = st.checkbox("تفعيل", value=False, key="tag_enable")

    if group_by_tag and tag_keyword.strip() and x_col in ("company_clean", "commune_clean"):
        keyword = tag_keyword.strip()
        # Group: matching items → keyword label, non-matching → "Others"
        chart_data[x_col] = chart_data[x_col].apply(
            lambda v: keyword if (v and keyword in str(v)) else "Others"
        )
        # Re-aggregate
        chart_data = chart_data.groupby(x_col, as_index=False)[y_col].sum()
        # Sort: keyword first, then Others last
        chart_data["_sort"] = chart_data[x_col].apply(
            lambda v: 0 if v == keyword else (1 if v == "Others" else 2)
        )
        chart_data = chart_data.sort_values(["_sort", y_col], ascending=[True, False]).drop(columns="_sort")

    # ═══════════════════════════════════════════════════════════
    #  NEW: "Selected vs Others" grouping for Pie charts (multiselect mode)
    # ═══════════════════════════════════════════════════════════
    group_selected = False
    if chart_type == "Pie" and x_col in ("company_clean", "commune_clean") and not group_by_tag:
        # Only show the toggle when Pie is selected AND the X axis is Company or Commune
        group_selected = st.checkbox(
            "اجمع غير المحدد في 'أخرى'",
            value=False,
            help="عند تحديد شركات/بلديات محددة أعلاه، يتم دمج الباقي في شريحة واحدة 'أخرى' لمقارنة تحديدك مع الباقي.",
        )

    if group_selected and x_col in ("company_clean", "commune_clean") and not group_by_tag:
        # Determine which items were explicitly selected
        if x_col == "company_clean" and selected_companies:
            selected_set = set(selected_companies)
        elif x_col == "commune_clean" and selected_communes:
            selected_set = set(selected_communes)
        else:
            selected_set = set()

        if selected_set:
            # Rebuild chart_data: selected items stay as-is, everything else becomes "Others"
            chart_data[x_col] = chart_data[x_col].apply(
                lambda v: v if v in selected_set else "Others"
            )
            # Re-aggregate after grouping
            chart_data = chart_data.groupby(x_col, as_index=False)[y_col].sum()
            # Sort so "Others" is always last, selected items sorted by value descending
            chart_data["_sort"] = chart_data[x_col].apply(lambda v: 1 if v == "Others" else 0)
            chart_data = chart_data.sort_values(["_sort", y_col], ascending=[True, False]).drop(columns="_sort")

    try:
        if chart_type == "Bar":
            custom_fig = px.bar(chart_data, x=x_col, y=y_col)
        elif chart_type == "Line":
            custom_fig = px.line(chart_data, x=x_col, y=y_col, markers=True)
        elif chart_type == "Scatter":
            custom_fig = px.scatter(chart_data, x=x_col, y=y_col, size=y_col if y_col != "Count" else None)
        else:
            custom_fig = px.pie(chart_data, names=x_col, values=y_col, hole=0.4)
        custom_fig = apply_dark(custom_fig)
        # Accent color rotation for variety
        accent_colors = ["#38BDF8", "#34D399", "#A78BFA", "#FBBF24", "#F87171", "#2DD4BF"]
        if chart_type != "Pie":
            custom_fig.update_traces(marker_color=accent_colors[0])
        else:
            custom_fig.update_traces(marker_colors=accent_colors)
        st.plotly_chart(custom_fig, use_container_width=True)
    except Exception as e:
        st.error(f"Couldn\'t build that chart with these choices: {e}")

# ─────────────────────────────────────────────────────────────
#  TAB: GROUPS
# ─────────────────────────────────────────────────────────────
with tab_groups:
    st.subheader("التجميع التلقائي")
    st.caption(
       
        "يتم تجميع أسماء الشركات والبلديات تلقائياً عندما تكون متشابهة بنسبة لا تقل عن 90/100، وذلك لدمج الأخطاء الإملائية وتناقضات الاستخراج. تعرض هذه النافذة كل مجموعة تم فيها دمج أكثر من تهجئة أصلية مختلفة، حتى تتمكن من مراجعتها بصرياً والتأكد من صحة التجميع. لإصلاح عملية دمج خاطئة، انتقل إلى   'تصحيح التجميعات الخاطئة'   في الاسفل"
    )

    st.markdown("### الشركات")
    company_groups = (
        filtered.groupby("company_clean")["company_name"]
        .unique()
        .reset_index()
    )
    company_groups["num_variants"] = company_groups["company_name"].apply(len)
    merged_company_groups = company_groups[company_groups["num_variants"] > 1].sort_values(
        "num_variants", ascending=False
    )

    if merged_company_groups.empty:
        st.info("لم يتم دمج أي أسماء شركات — جميع الأسماء في الفلتر الحالي مميزة بالفعل.")
    else:
        for _, row in merged_company_groups.iterrows():
            with st.expander(f"{row['company_clean']}  ({row['num_variants']} أسماء متشابهة)"):
                for variant in row["company_name"]:
                    st.write(f"- {variant}")

    st.divider()

    st.markdown("### البلديات")
    commune_groups = (
        filtered.groupby("commune_clean")["commune"]
        .unique()
        .reset_index()
    )
    commune_groups["num_variants"] = commune_groups["commune"].apply(len)
    merged_commune_groups = commune_groups[commune_groups["num_variants"] > 1].sort_values(
        "num_variants", ascending=False
    )

    if merged_commune_groups.empty:
        st.info("لم يتم دمج أي أسماء بلديات.")
    else:
        for _, row in merged_commune_groups.iterrows():
            with st.expander(f"{row['commune_clean']}  ({row['num_variants']} variants)"):
                for variant in row["commune"]:
                    st.write(f"- {variant}")

# ─────────────────────────────────────────────────────────────
#  TAB: FIX
# ─────────────────────────────────────────────────────────────

    st.divider()
    st.markdown("---")
    st.subheader("تصحيح التجميعات الخاطئة")
    st.caption(
        "Pick a group below and edit the target name for any variant. Set a variant\'s "
        "target back to its own original spelling to split it out of a wrong merge, or "
        "type a different existing group name to manually merge it elsewhere. "
        "Changes are saved permanently and apply the next time the dashboard loads."
    )

    entity_type = st.radio("نوع الكيان", ["الشركة", "البلدية"], horizontal=True)

    if entity_type == "الشركة":
        source_col, clean_col, override_key = "company_name", "company_clean", "company"
    else:
        source_col, clean_col, override_key = "commune", "commune_clean", "commune"

    groups_df = (
        filtered.groupby(clean_col)[source_col]
        .unique()
        .reset_index()
    )
    groups_df["num_variants"] = groups_df[source_col].apply(len)
    mergeable = groups_df[groups_df["num_variants"] > 1].sort_values("num_variants", ascending=False)

    if mergeable.empty:
        st.info("لا توجد مجموعات مدمجة لمراجعة هذا النوع.")
    else:
        group_options = mergeable[clean_col].tolist()
        selected_group = st.selectbox("اختر مجموعة للمراجعة", group_options)

        variants = mergeable[mergeable[clean_col] == selected_group][source_col].iloc[0]

        st.write(f"تعديل المجموعة: **{selected_group}**")
        edits = {}
        for variant in variants:
            new_value = st.text_input(
                f"الهدف لـ: {variant}",
                value=selected_group,
                key=f"{override_key}_{variant}",
            )
            edits[variant] = new_value

        if st.button("حفظ التغييرات", key=f"save_{override_key}_{selected_group}"):
            overrides = load_overrides()
            overrides.setdefault(override_key, {})
            for variant, new_value in edits.items():
                new_value = new_value.strip()
                if new_value and new_value != selected_group:
                    overrides[override_key][variant] = new_value
                elif variant in overrides[override_key]:
                    del overrides[override_key][variant]
            save_overrides(overrides)
            load_data.clear()
            st.success("تم الحفظ — إعادة التحميل بالتغييرات.")
            st.rerun()

    st.divider()
    st.markdown("**التجاوزات اليدوية الحالية**")
    overrides = load_overrides()
    active = overrides.get(override_key, {})
    if not active:
        st.write("لا توجد تجاوزات يدوية لهذا النوع بعد.")
    else:
        for original, target in list(active.items()):
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"{original} → {target}")
            if col_b.button("إزالة", key=f"remove_{override_key}_{original}"):
                del overrides[override_key][original]
                save_overrides(overrides)
                load_data.clear()
                st.rerun()

# ─────────────────────────────────────────────────────────────
#  TAB: ABOUT
# ─────────────────────────────────────────────────────────────
