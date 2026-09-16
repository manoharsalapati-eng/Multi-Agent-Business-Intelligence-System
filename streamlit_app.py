"""
Streamlit frontend for the Multi-Agent Business Intelligence System.

This is a thin client — it ONLY calls the FastAPI backend over HTTP.
No agent or LangGraph logic lives here.

Two sections:
  1. Dashboard  — headline metrics + charts, loaded from GET /stats on open.
  2. Assistant  — natural-language chat, answered by POST /query.

Start with:
    streamlit run streamlit_app.py
"""

import inspect
import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

import altair as alt
import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = os.getenv("API_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Chart tokens
#
# Categorical slots 1 and 2 of a colourblind-safe palette, stepped for a dark
# surface. Validated as a pair: worst-case CVD separation ΔE 26.8 (protan),
# normal-vision ΔE 31.8, both ≥ 3:1 contrast against the chart surface.
# Text never wears a series colour — labels use the ink tokens below.
# ---------------------------------------------------------------------------
SERIES_1 = "#3987e5"       # blue   — historical / primary magnitude
SERIES_2 = "#d95926"       # orange — forecast
SURFACE = "#161b22"        # chart surface
GRID = "#30363d"           # recessive gridlines and axis domain
TEXT_PRIMARY = "#c9d1d9"
TEXT_MUTED = "#8b949e"
FONT = "Inter, sans-serif"

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Multi-Agent BI System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — premium dark design
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Dark gradient background */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        color: #c9d1d9;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }

    /* Header banner */
    .hero-banner {
        background: linear-gradient(90deg, #1f6feb 0%, #58a6ff 50%, #79c0ff 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(31,111,235,0.35);
    }
    .hero-banner h1 {
        color: #ffffff !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        margin: 0 0 0.4rem 0 !important;
    }
    .hero-banner p {
        color: rgba(255,255,255,0.85) !important;
        font-size: 1rem !important;
        margin: 0 !important;
    }

    /* KPI stat tiles */
    .kpi-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        height: 100%;
    }
    .kpi-label {
        color: #8b949e;
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        color: #c9d1d9;
        font-size: 1.75rem;
        font-weight: 700;
        line-height: 1.15;
    }
    .kpi-value.accent { color: #58a6ff; }
    .kpi-value.alert  { color: #e66767; }
    .kpi-sub {
        color: #8b949e;
        font-size: 0.75rem;
        margin-top: 0.3rem;
    }

    /* Section headings */
    .section-title {
        color: #c9d1d9;
        font-size: 1.05rem;
        font-weight: 600;
        margin: 1.4rem 0 0.2rem 0;
    }
    .section-sub {
        color: #8b949e;
        font-size: 0.82rem;
        margin-bottom: 0.6rem;
    }

    /* Agent badge styling */
    .agent-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-right: 4px;
    }
    .badge-sql    { background: rgba(31,111,235,0.2);  color: #58a6ff; border: 1px solid #1f6feb; }
    .badge-rag    { background: rgba(63,185,80,0.2);   color: #56d364; border: 1px solid #3fb950; }
    .badge-forecast { background: rgba(210,153,34,0.2); color: #e3b341; border: 1px solid #d2961f; }

    /* Router reasoning callout */
    .router-note {
        background: rgba(31,111,235,0.08);
        border-left: 3px solid #1f6feb;
        border-radius: 6px;
        padding: 8px 12px;
        color: #8b949e;
        font-size: 0.83rem;
        margin: 4px 0 12px 0;
    }

    /* Chat message cards */
    .stChatMessage {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
        margin-bottom: 1rem !important;
        padding: 0.5rem !important;
    }

    /* Chat input box */
    .stChatInputContainer {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 12px !important;
    }
    .stChatInputContainer textarea {
        color: #c9d1d9 !important;
    }

    /* Dataframe / table */
    .stDataFrame {
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    /* Spinner override */
    .stSpinner > div > div {
        border-top-color: #58a6ff !important;
    }

    /* Section dividers */
    hr {
        border-color: #30363d !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Streamlit width compatibility
#
# Streamlit renamed `use_container_width=True` to `width="stretch"`. Older
# versions only understand the former, newer ones warn on it. Detecting which
# one a widget accepts keeps this app working on any installed version.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _supports_width(func_name: str) -> bool:
    func = getattr(st, func_name, None)
    try:
        return "width" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


def stretch(func_name: str) -> Dict[str, Any]:
    """Returns the right 'fill the container' keyword for this Streamlit build."""
    if _supports_width(func_name):
        return {"width": "stretch"}
    return {"use_container_width": True}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_money(value: Any) -> str:
    """Formats a number as compact currency, e.g. $2.23M / $45.1K / $912."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(n) >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if abs(n) >= 1_000:
        return f"${n / 1_000:.1f}K"
    return f"${n:,.0f}"


def fmt_int(value: Any) -> str:
    """Formats a whole number with thousands separators."""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def kpi_card(label: str, value: str, sub: str = "", tone: str = "") -> str:
    """Builds the HTML for one stat tile."""
    tone_class = f" {tone}" if tone else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value{tone_class}">{value}</div>'
        f"{sub_html}"
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Chart builders
#
# Each takes plain list-of-dicts (exactly what the API returns) and returns an
# Altair chart, so they can be unit-tested without running Streamlit.
# ---------------------------------------------------------------------------

def _style(chart: alt.Chart) -> alt.Chart:
    """
    Applies the shared dark-surface theme to a top-level chart.

    autosize is pinned to "fit-x" so the chart stretches horizontally to its
    container but keeps the explicit height it was given — plain "fit" (what
    Streamlit applies by default for container-width charts) squashes the
    vertical axis and collapses categorical bands on top of each other.
    """
    return (
        chart.properties(
            background="transparent",
            autosize=alt.AutoSizeParams(type="fit-x", contains="padding"),
        )
        .configure_view(strokeWidth=0, fill="transparent")
        .configure_axis(
            grid=True,
            gridColor=GRID,
            gridWidth=1,
            gridOpacity=1,
            domainColor=GRID,
            tickColor=GRID,
            labelColor=TEXT_MUTED,
            titleColor=TEXT_MUTED,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
        )
        .configure_legend(
            labelColor=TEXT_PRIMARY,
            titleColor=TEXT_MUTED,
            labelFont=FONT,
            titleFont=FONT,
            labelFontSize=11,
            titleFontSize=11,
            symbolType="stroke",
            symbolStrokeWidth=3,
        )
        .configure_title(color=TEXT_PRIMARY, font=FONT, fontSize=13, anchor="start")
    )


def revenue_trend_chart(rows: List[Dict[str, Any]]) -> Optional[alt.Chart]:
    """Monthly revenue over time. One series, so no legend — the title names it."""
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if "month" not in df.columns or "revenue" not in df.columns:
        return None
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
    df = df.dropna(subset=["revenue"])
    if df.empty:
        return None

    hover = alt.selection_point(
        fields=["month"], nearest=True, on="mouseover", empty=False, clear="mouseout"
    )
    base = alt.Chart(df).encode(
        x=alt.X(
            "month:O",
            title=None,
            axis=alt.Axis(labelAngle=-45, labelOverlap="greedy"),
        ),
        y=alt.Y("revenue:Q", title="Revenue ($)", axis=alt.Axis(format="~s", tickCount=5)),
    )
    area = base.mark_area(color=SERIES_1, opacity=0.10)
    line = base.mark_line(color=SERIES_1, strokeWidth=2, strokeCap="round")
    # Wide transparent hit area so the crosshair is easy to catch.
    hit = (
        base.mark_point(size=400, opacity=0)
        .add_params(hover)
        .encode(
            tooltip=[
                alt.Tooltip("month:O", title="Month"),
                alt.Tooltip("revenue:Q", title="Revenue", format="$,.0f"),
                alt.Tooltip("units:Q", title="Units", format=","),
            ]
        )
    )
    rule = (
        base.mark_rule(color=TEXT_MUTED, strokeWidth=1)
        .transform_filter(hover)
    )
    dot = (
        base.mark_point(
            size=90, filled=True, color=SERIES_1, stroke=SURFACE, strokeWidth=2
        )
        .transform_filter(hover)
    )
    return _style(
        alt.layer(area, line, rule, dot, hit)
        .properties(height=260, title="Revenue trend by month")
    )


def _magnitude_bar(
    rows: List[Dict[str, Any]],
    category_field: str,
    value_field: str,
    title: str,
    category_title: str,
) -> Optional[alt.Chart]:
    """
    Horizontal bar for 'compare magnitude'. One hue (length carries the value),
    with a direct label at each bar tip so nothing depends on colour alone.
    """
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if category_field not in df.columns or value_field not in df.columns:
        return None
    df[value_field] = pd.to_numeric(df[value_field], errors="coerce")
    df = df.dropna(subset=[value_field])
    if df.empty:
        return None

    order = df.sort_values(value_field, ascending=False)[category_field].tolist()
    # 22% headroom on the value axis so the direct label at each bar tip has
    # room to render instead of being clipped at the plot edge.
    headroom = float(df[value_field].max()) * 1.22 or 1.0
    base = alt.Chart(df).encode(
        y=alt.Y(f"{category_field}:N", sort=order, title=None),
        x=alt.X(
            f"{value_field}:Q",
            title=category_title,
            axis=alt.Axis(format="~s", tickCount=5),
            scale=alt.Scale(domain=[0, headroom], nice=False),
        ),
    )
    bars = base.mark_bar(
        color=SERIES_1, cornerRadiusEnd=4, height=22
    ).encode(
        tooltip=[
            alt.Tooltip(f"{category_field}:N", title=category_field.title()),
            alt.Tooltip(f"{value_field}:Q", title="Revenue", format="$,.0f"),
        ]
    )
    labels = base.mark_text(
        align="left", dx=6, color=TEXT_PRIMARY, font=FONT, fontSize=11
    ).encode(text=alt.Text(f"{value_field}:Q", format="$,.0f"))

    height = max(160, 54 * len(df))
    return _style(
        alt.layer(bars, labels).properties(height=height, title=title)
    )


def region_chart(rows: List[Dict[str, Any]]) -> Optional[alt.Chart]:
    """Revenue split by sales region."""
    return _magnitude_bar(rows, "region", "revenue", "Revenue by region", "Revenue ($)")


def top_products_chart(rows: List[Dict[str, Any]]) -> Optional[alt.Chart]:
    """Best-selling products by revenue."""
    return _magnitude_bar(
        rows, "product", "revenue", "Top products by revenue", "Revenue ($)"
    )


def forecast_chart(
    historical: List[Dict[str, Any]], predicted: List[Dict[str, Any]]
) -> Optional[alt.Chart]:
    """
    Historical actuals against the model's forecast, with the confidence band
    the model already computed drawn as a wash behind the forecast line.
    Two series, so a legend is always present.
    """
    frames = []
    band_df = None

    if historical:
        h = pd.DataFrame(historical)
        if {"ds", "y"}.issubset(h.columns):
            h = h.rename(columns={"ds": "date", "y": "value"})
            h["series"] = "Historical"
            frames.append(h[["date", "value", "series"]])

    if predicted:
        p = pd.DataFrame(predicted)
        if {"ds", "yhat"}.issubset(p.columns):
            band_cols = {"yhat_lower", "yhat_upper"}
            if band_cols.issubset(p.columns):
                # Renamed to "value" so this layer shares the line layer's
                # field — different field names make Vega-Lite draw two
                # y-axes (or drop the axis entirely).
                band_df = p.rename(
                    columns={
                        "ds": "date",
                        "yhat_lower": "value",
                        "yhat_upper": "value_upper",
                    }
                )[["date", "value", "value_upper"]]
            f = p.rename(columns={"ds": "date", "yhat": "value"})
            f["series"] = "Forecast"
            frames.append(f[["date", "value", "series"]])

    if not frames:
        return None

    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    if df.empty:
        return None

    layers = []

    if band_df is not None and not band_df.empty:
        band_df = band_df.copy()
        band_df["date"] = pd.to_datetime(band_df["date"], errors="coerce")
        band_df["value"] = pd.to_numeric(band_df["value"], errors="coerce")
        band_df["value_upper"] = pd.to_numeric(band_df["value_upper"], errors="coerce")
        band_df = band_df.dropna()
        if not band_df.empty:
            layers.append(
                alt.Chart(band_df)
                .mark_area(color=SERIES_2, opacity=0.10)
                .encode(
                    x=alt.X("date:T", title=None),
                    y=alt.Y(
                        "value:Q",
                        title="Value",
                        axis=alt.Axis(format="~s", tickCount=5),
                    ),
                    y2=alt.Y2("value_upper:Q"),
                )
            )

    lines = (
        alt.Chart(df)
        .mark_line(strokeWidth=2, strokeCap="round")
        .encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("value:Q", title="Value", axis=alt.Axis(format="~s", tickCount=5)),
            color=alt.Color(
                "series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Historical", "Forecast"], range=[SERIES_1, SERIES_2]
                ),
                legend=alt.Legend(orient="top"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("value:Q", title="Value", format=",.0f"),
                alt.Tooltip("series:N", title="Series"),
            ],
        )
    )
    layers.append(lines)

    return _style(
        alt.layer(*layers).properties(
            height=280, title="Forecast with confidence band"
        )
    )


def sql_auto_chart(rows: List[Dict[str, Any]]) -> Optional[alt.Chart]:
    """
    Draws a bar chart for SQL results that are shaped like 'one label column,
    one number column'. Returns None when a chart would not help, in which case
    the caller shows only the table.
    """
    if not rows or len(rows) < 2 or len(rows) > 25:
        return None
    df = pd.DataFrame(rows)
    if df.shape[1] != 2:
        return None

    numeric_cols, label_cols = [], []
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().all():
            numeric_cols.append(col)
        else:
            label_cols.append(col)

    if len(numeric_cols) != 1 or len(label_cols) != 1:
        return None

    label_col, value_col = label_cols[0], numeric_cols[0]
    df[value_col] = pd.to_numeric(df[value_col])
    if df[label_col].nunique() != len(df):
        return None

    order = df.sort_values(value_col, ascending=False)[label_col].astype(str).tolist()
    df[label_col] = df[label_col].astype(str)

    headroom = float(df[value_col].max()) * 1.22 or 1.0
    base = alt.Chart(df).encode(
        y=alt.Y(f"{label_col}:N", sort=order, title=None),
        x=alt.X(
            f"{value_col}:Q",
            title=str(value_col),
            axis=alt.Axis(format="~s", tickCount=5),
            scale=alt.Scale(domain=[0, headroom], nice=False),
        ),
    )
    bars = base.mark_bar(color=SERIES_1, cornerRadiusEnd=4, height=22).encode(
        tooltip=[
            alt.Tooltip(f"{label_col}:N", title=str(label_col)),
            alt.Tooltip(f"{value_col}:Q", title=str(value_col), format=",.2f"),
        ]
    )
    labels = base.mark_text(
        align="left", dx=6, color=TEXT_PRIMARY, font=FONT, fontSize=11
    ).encode(text=alt.Text(f"{value_col}:Q", format=",.0f"))

    height = max(160, 54 * len(df))
    return _style(alt.layer(bars, labels).properties(height=height))


# ---------------------------------------------------------------------------
# Backend calls
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stats() -> Dict[str, Any]:
    """Loads dashboard metrics. Never raises — the UI shows the reason instead."""
    try:
        response = requests.get(f"{API_URL}/stats", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {
            "available": False,
            "message": (
                f"Cannot reach the backend at `{API_URL}`. "
                "Start it with `uvicorn app.main:app --reload --port 8000`."
            ),
        }
    except Exception as e:
        return {"available": False, "message": f"Could not load statistics: {e}"}


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 1.2rem 0 0.5rem 0;">
            <div style="font-size:2.8rem;">🤖</div>
            <div style="font-size:1.1rem; font-weight:700; color:#58a6ff; margin-top:4px;">BI Assistant</div>
            <div style="font-size:0.78rem; color:#8b949e; margin-top:2px;">Powered by GPT-OSS 120B</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("**💡 What can I help with?**")
    st.markdown(
        """
        <div style="color:#8b949e; font-size:0.85rem; line-height:1.7rem;">
        📊 &nbsp;Sales & revenue analysis<br>
        📦 &nbsp;Inventory & stock levels<br>
        👥 &nbsp;Customer segments & LTV<br>
        📋 &nbsp;Company policies & reports<br>
        📈 &nbsp;Sales forecasting & trends
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    st.markdown("**🧠 Specialist agents**")
    st.markdown(
        """
        <div style="color:#8b949e; font-size:0.82rem; line-height:1.6rem;">
        <b style="color:#58a6ff;">SQL</b> — queries the sales database<br>
        <b style="color:#56d364;">RAG</b> — searches policy documents<br>
        <b style="color:#e3b341;">Forecast</b> — predicts future trends<br>
        <b style="color:#c9d1d9;">Synthesizer</b> — merges the answers
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.button("🔄 Refresh dashboard", **stretch("button")):
        fetch_stats.clear()
        st.rerun()

    if st.button("🗑️ Clear chat", **stretch("button")):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Hero banner
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero-banner">
        <h1>🤖 Multi-Agent Business Intelligence</h1>
        <p>Ask any business question — sales analytics, company policies, or future forecasts.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
stats = fetch_stats()

if not stats.get("available"):
    st.warning(f"📊 Dashboard unavailable — {stats.get('message', 'unknown error')}")
else:
    period = ""
    if stats.get("first_date") and stats.get("last_date"):
        period = f"{stats['first_date']} → {stats['last_date']}"

    st.markdown('<div class="section-title">Business overview</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-sub">{fmt_int(stats.get("total_orders"))} sales records'
        f'{" · " + period if period else ""}</div>',
        unsafe_allow_html=True,
    )

    low_stock_count = stats.get("low_stock_count", 0)
    cols = st.columns(4)
    cards = [
        kpi_card(
            "Total revenue",
            fmt_money(stats.get("total_revenue")),
            f"Top product: {stats.get('top_product') or '—'}",
            tone="accent",
        ),
        kpi_card(
            "Units sold",
            fmt_int(stats.get("total_units")),
            f"{fmt_int(stats.get('total_orders'))} orders",
        ),
        kpi_card(
            "Avg order value",
            fmt_money(stats.get("avg_order_value")),
            f"{fmt_int(stats.get('customer_count'))} customers",
        ),
        kpi_card(
            "Reorder alerts",
            fmt_int(low_stock_count),
            "products at or below reorder point",
            tone="alert" if low_stock_count else "",
        ),
    ]
    for col, card in zip(cols, cards):
        col.markdown(card, unsafe_allow_html=True)

    trend = revenue_trend_chart(stats.get("revenue_by_month", []))
    if trend is not None:
        st.markdown("")
        st.altair_chart(trend, **stretch("altair_chart"))

    left, right = st.columns(2)
    region = region_chart(stats.get("revenue_by_region", []))
    if region is not None:
        left.altair_chart(region, **stretch("altair_chart"))
    products = top_products_chart(stats.get("top_products", []))
    if products is not None:
        right.altair_chart(products, **stretch("altair_chart"))

    if stats.get("low_stock"):
        with st.expander(f"⚠️ {low_stock_count} product(s) need reordering", expanded=False):
            st.dataframe(pd.DataFrame(stats["low_stock"]), **stretch("dataframe"))

st.markdown("---")


# ---------------------------------------------------------------------------
# Helper: render rich results attached to a message
# ---------------------------------------------------------------------------
def render_rich_data(data: dict):
    """Renders agent badges, routing reasoning, SQL tables, charts and sources."""
    agents_used = data.get("agents_used", [])

    # ── Agent badges + timing ─────────────────────────────────────────────
    if agents_used:
        badges_html = "".join(
            f'<span class="agent-badge badge-{a}">{a}</span>' for a in agents_used
        )
        elapsed = data.get("elapsed_seconds")
        timing = (
            f'<span style="color:#8b949e; font-size:0.78rem; margin-left:8px;">'
            f"answered in {elapsed:.2f}s</span>"
            if isinstance(elapsed, (int, float)) and elapsed
            else ""
        )
        st.markdown(
            f'<div style="margin: 6px 0 8px 0;">Agents used: {badges_html}{timing}</div>',
            unsafe_allow_html=True,
        )

    # ── Why these agents? (router reasoning) ──────────────────────────────
    reasoning = (data.get("routing_reasoning") or "").strip()
    if reasoning:
        st.markdown(
            f'<div class="router-note"><b>Why these agents?</b> {reasoning}</div>',
            unsafe_allow_html=True,
        )

    # ── SQL results: chart when it helps, always the table ────────────────
    sql = data.get("sql_result")
    if sql and sql.get("sql_rows"):
        with st.expander("📊 SQL Query Results", expanded=True):
            rows = sql["sql_rows"]
            chart = sql_auto_chart(rows)
            if chart is not None:
                st.altair_chart(chart, **stretch("altair_chart"))
            st.dataframe(pd.DataFrame(rows), **stretch("dataframe"))
            with st.expander("🔍 Generated SQL", expanded=False):
                st.code(sql.get("sql_query", ""), language="sql")

    # ── Forecast chart with confidence band ───────────────────────────────
    forecast = data.get("forecast_result")
    if forecast and (forecast.get("historical_data") or forecast.get("forecast_data")):
        with st.expander("📈 Forecast Chart", expanded=True):
            st.caption(f"Model used: **{forecast.get('model_used', 'Unknown')}**")
            chart = forecast_chart(
                forecast.get("historical_data", []),
                forecast.get("forecast_data", []),
            )
            if chart is not None:
                st.altair_chart(chart, **stretch("altair_chart"))
                st.caption(
                    "The shaded band is the model's confidence interval — the "
                    "wider it gets, the less certain the prediction."
                )
            else:
                st.info("Not enough data points to draw a forecast chart.")

    # ── RAG source snippets ───────────────────────────────────────────────
    rag = data.get("rag_result")
    if rag and rag.get("retrieved_chunks"):
        with st.expander("📚 Retrieved Source Documents", expanded=False):
            for chunk in rag["retrieved_chunks"]:
                src = chunk.get("source", "unknown")
                content = chunk.get("content", "")
                st.markdown(f"**Source:** `{src}`")
                st.markdown(
                    f'<div style="background:#161b22;border:1px solid #30363d;'
                    f'border-radius:8px;padding:10px;font-size:0.85rem;'
                    f'color:#8b949e;margin-bottom:8px;">{content[:500]}'
                    f'{"..." if len(content) > 500 else ""}</div>',
                    unsafe_allow_html=True,
                )

    # ── Errors ────────────────────────────────────────────────────────────
    errors = data.get("errors", [])
    if errors:
        with st.expander("⚠️ Agent Warnings", expanded=False):
            for err in errors:
                st.warning(err)


# ---------------------------------------------------------------------------
# Send query to API
# ---------------------------------------------------------------------------
def send_query(user_query: str):
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("🔍 Routing query through agents..."):
            response = None
            try:
                response = requests.post(
                    f"{API_URL}/query",
                    json={"query": user_query},
                    timeout=180,
                )
                response.raise_for_status()
                data = response.json()

                answer = data.get("final_answer", "No answer returned.")
                st.markdown(answer)
                render_rich_data(data)

                # Persist message with attached data for replay on re-render
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "data": data}
                )

            except requests.exceptions.ConnectionError:
                err_msg = (
                    "❌ **Cannot connect to the backend API.**\n\n"
                    f"Make sure the FastAPI server is running at `{API_URL}`.\n\n"
                    "```bash\nuvicorn app.main:app --reload --port 8000\n```"
                )
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except requests.exceptions.Timeout:
                err_msg = "⏱️ **Request timed out.** The query may be too complex — please try again."
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except requests.exceptions.HTTPError as e:
                detail = str(e)
                if response is not None:
                    try:
                        detail = response.json().get("detail", str(e))
                    except Exception:
                        pass
                err_msg = f"❌ **API Error:** {detail}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except Exception as e:
                err_msg = f"❌ **Unexpected error:** {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})


# ---------------------------------------------------------------------------
# Assistant section
# ---------------------------------------------------------------------------
st.markdown('<div class="section-title">Ask the assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-sub">Your question is routed to the right specialist agents automatically.</div>',
    unsafe_allow_html=True,
)

SUGGESTED_QUERIES = [
    "💰 Total revenue by region last 3 months?",
    "📦 What products are below reorder point?",
    "📋 What is our return policy?",
    "📈 Forecast Widget A sales for the next 30 days",
    "🚀 Top 3 products by total revenue?",
]

cols = st.columns(len(SUGGESTED_QUERIES))
for col, sq in zip(cols, SUGGESTED_QUERIES):
    if col.button(sq, **stretch("button")):
        # Strip the emoji prefix before sending
        st.session_state.pending_query = sq.split(" ", 1)[1] if " " in sq else sq

# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
        st.markdown(msg["content"])
        # Replay rich data (tables, charts, snippets) for assistant messages
        if msg["role"] == "assistant" and "data" in msg:
            render_rich_data(msg["data"])

# ---------------------------------------------------------------------------
# Handle suggested-query button presses
# ---------------------------------------------------------------------------
if st.session_state.pending_query:
    pq = st.session_state.pending_query
    st.session_state.pending_query = None
    send_query(pq)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask a business question… (e.g. 'What were top-selling products in Q3?')")
if user_input:
    send_query(user_input)
