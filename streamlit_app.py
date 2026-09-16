"""
Streamlit frontend for the Multi-Agent Business Intelligence System.

This is a thin client — it ONLY calls the FastAPI backend over HTTP.
No agent or LangGraph logic lives here.

Start with:
    streamlit run streamlit_app.py
"""

import os
import json
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = os.getenv("API_URL", "http://localhost:8000")

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

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
    }
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #58a6ff !important;
        font-size: 1.6rem !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 1.2rem 0 0.5rem 0;">
            <div style="font-size:2.8rem;">🤖</div>
            <div style="font-size:1.1rem; font-weight:700; color:#58a6ff; margin-top:4px;">BI Assistant</div>
            <div style="font-size:0.78rem; color:#8b949e; margin-top:2px;">Powered by Llama 3.3 70B</div>
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

    if st.button("🗑️ Clear Chat", use_container_width=True):
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
# Helper: render rich results attached to a message
# ---------------------------------------------------------------------------
def render_rich_data(data: dict):
    """Renders SQL tables, forecast charts, and RAG snippets."""
    agents_used = data.get("agents_used", [])

    # ── Agent badges ──────────────────────────────────────────────────────
    if agents_used:
        badges_html = "".join(
            f'<span class="agent-badge badge-{a}">{a}</span>'
            for a in agents_used
        )
        st.markdown(
            f'<div style="margin: 6px 0 12px 0;">Agents used: {badges_html}</div>',
            unsafe_allow_html=True,
        )

    # ── SQL results table ─────────────────────────────────────────────────
    sql = data.get("sql_result")
    if sql and sql.get("sql_rows"):
        with st.expander("📊 SQL Query Results", expanded=True):
            df = pd.DataFrame(sql["sql_rows"])
            st.dataframe(df, use_container_width=True)
            with st.expander("🔍 Generated SQL", expanded=False):
                st.code(sql.get("sql_query", ""), language="sql")

    # ── Forecast chart ────────────────────────────────────────────────────
    forecast = data.get("forecast_result")
    if forecast and (forecast.get("historical_data") or forecast.get("forecast_data")):
        with st.expander("📈 Forecast Chart", expanded=True):
            hist = forecast.get("historical_data", [])
            pred = forecast.get("forecast_data", [])

            model_label = forecast.get("model_used", "Unknown Model")
            st.caption(f"Model used: **{model_label}**")

            if hist:
                hist_df = pd.DataFrame(hist).rename(columns={"ds": "Date", "y": "Historical"}).set_index("Date")
            else:
                hist_df = pd.DataFrame()

            if pred:
                pred_df = pd.DataFrame(pred).rename(columns={"ds": "Date", "yhat": "Forecast"})
                pred_df = pred_df[["Date", "Forecast"]].set_index("Date")
            else:
                pred_df = pd.DataFrame()

            # Merge for combined chart
            if not hist_df.empty and not pred_df.empty:
                combined = hist_df.join(pred_df, how="outer")
            elif not hist_df.empty:
                combined = hist_df
            else:
                combined = pred_df

            st.line_chart(combined, use_container_width=True)

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
                    f'color:#8b949e;margin-bottom:8px;">{content[:500]}{"..." if len(content)>500 else ""}</div>',
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
                try:
                    detail = response.json().get("detail", str(e))
                except Exception:
                    detail = str(e)
                err_msg = f"❌ **API Error:** {detail}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})

            except Exception as e:
                err_msg = f"❌ **Unexpected error:** {str(e)}"
                st.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})


# ---------------------------------------------------------------------------
# Suggested queries
# ---------------------------------------------------------------------------
SUGGESTED_QUERIES = [
    "💰 Total revenue by region last 3 months?",
    "📦 What products are below reorder point?",
    "📋 What is our return policy?",
    "📈 Forecast Widget A sales for the next 30 days",
    "🚀 Top 3 products by total revenue?",
]

st.markdown("**💡 Try a sample query:**")
cols = st.columns(len(SUGGESTED_QUERIES))
for col, sq in zip(cols, SUGGESTED_QUERIES):
    if col.button(sq, use_container_width=True):
        # Strip the emoji prefix before sending
        clean_q = sq.split(" ", 1)[1] if " " in sq else sq
        st.session_state.pending_query = clean_q

# ---------------------------------------------------------------------------
# Chat history display
# ---------------------------------------------------------------------------
st.markdown("---")
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])
            # Replay rich data (tables, charts, snippets) for assistant messages
            if msg["role"] == "assistant" and "data" in msg:
                render_rich_data(msg["data"])

# ---------------------------------------------------------------------------
# Handle suggested-query button presses
# ---------------------------------------------------------------------------
if "pending_query" in st.session_state and st.session_state.pending_query:
    pq = st.session_state.pending_query
    st.session_state.pending_query = None
    send_query(pq)

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
user_input = st.chat_input("Ask a business question… (e.g. 'What were top-selling products in Q3?')")
if user_input:
    send_query(user_input)
