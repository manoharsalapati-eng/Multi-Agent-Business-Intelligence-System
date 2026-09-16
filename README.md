# Multi-Agent Business Intelligence System

A fully local, open-source Multi-Agent BI system powered by **GPT-OSS 120B** (via Groq's free tier), **LangGraph**, **ChromaDB**, **SQLite**, **FastAPI**, and **Streamlit**.

Ask natural-language business questions — the system automatically routes them to the right specialist agent(s), runs them in parallel, and synthesizes a coherent answer.

```
User Question
     │
     ▼
 Router Agent  ──────────────────────────────────────────────────────────┐
     │                                                                   │
     ├──► SQL Agent        (structured sales/inventory/customer data)    │
     ├──► RAG Agent        (policy & report documents via ChromaDB)      │
     └──► Forecast Agent   (Prophet / ARIMA time-series prediction)      │
                                                                         │
                          Synthesizer Agent  ◄────────────────────────────┘
                                 │
                                 ▼
                          Final Business Answer
```

---

## ✨ Features

| Feature | Details |
|---|---|
| **LLM** | GPT-OSS 120B — Groq free tier |
| **Orchestration** | LangGraph state machine with parallel agent branches |
| **Structured DB** | SQLite with 12 months of synthetic sales data |
| **Vector Store** | ChromaDB (local persistent) + `all-MiniLM-L6-v2` embeddings |
| **Forecasting** | Prophet (auto-falls back to statsmodels ARIMA) |
| **API** | FastAPI — decoupled from UI, testable via curl/Postman |
| **UI** | Streamlit — dark dashboard + chat interface |
| **Dashboard** | Live KPIs, revenue trend, region & product breakdowns (no API key needed) |
| **Charts** | Altair — colourblind-safe palette, hover tooltips, forecast confidence bands |

---

## 🚀 Quick Start

> **Requires Python 3.10 or higher.** Check yours with `python --version`.

### 1. Get a Free Groq API Key

1. Visit [https://console.groq.com](https://console.groq.com) and sign up for free.
2. Navigate to **API Keys** → **Create API Key**.
3. Copy the key.

### 2. Clone & Install

```bash
cd Multi-Agent-Business-Intelligence-System
pip install -r requirements.txt
```

> **Windows / Prophet note:** Prophet installs cleanly on most systems. If you see a `cmdstanpy` error, the forecast agent will automatically fall back to `statsmodels ARIMA`.

### 3. Configure Environment

```bash
copy .env.example .env
```

Edit `.env` and paste your Groq API key:

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

### 4. Seed the Data

```bash
# Create SQLite DB with 12 months of synthetic sales data
python data/seed_db.py

# Embed company documents into ChromaDB (downloads ~90MB model on first run)
python data/seed_docs.py
```

### 5. Start the FastAPI Backend

```bash
uvicorn app.main:app --reload --port 8000
```

Test it independently (no UI needed):

```bash
# PowerShell
Invoke-RestMethod -Uri http://localhost:8000/query `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"query": "What is our total revenue by region?"}'

# curl
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is our return policy?"}'
```

### 6. Start the Streamlit Frontend

In a **separate terminal**:

```bash
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Project Structure

```
Multi-Agent-Business-Intelligence-System/
├── agents/
│   ├── router_agent.py         # Classifies query → sql/rag/forecast
│   ├── sql_agent.py            # SQL generation + guardrails + explanation
│   ├── rag_agent.py            # ChromaDB retrieval + context-locked answer
│   ├── forecast_agent.py       # Prophet/ARIMA forecast + explanation
│   └── synthesizer_agent.py    # Combines all agent outputs
├── app/
│   ├── graph.py                # LangGraph state machine definition
│   └── main.py                 # FastAPI app — POST /query endpoint
├── data/
│   ├── seed_db.py              # Creates db.sqlite with fake data
│   └── seed_docs.py            # Seeds ChromaDB with policy documents
├── utils/
│   ├── llm_client.py           # Shared Groq API wrapper (single place for model/key config)
│   └── db_stats.py             # Read-only dashboard queries (no LLM involved)
├── tests/
│   ├── test_sql_safety.py      # SQL guardrail + query cleaning
│   ├── test_graph_routing.py   # LangGraph node routing + router fallback
│   ├── test_dashboard_stats.py # Dashboard metric queries
│   └── test_charts.py          # Chart builders + formatting helpers
├── streamlit_app.py            # Streamlit UI — dashboard + chat
├── conftest.py                 # Puts the project root on sys.path for pytest
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## 🔌 API Reference

### `POST /query`

**Request:**
```json
{
  "query": "What were the top-selling products in Q3?"
}
```

**Response:**
```json
{
  "final_answer": "...",
  "agents_used": ["sql"],
  "routing_reasoning": "...",
  "sql_result": {
    "sql_query": "SELECT ...",
    "sql_rows": [...],
    "explanation": "..."
  },
  "rag_result": null,
  "forecast_result": null,
  "errors": [],
  "elapsed_seconds": 2.14
}
```

### `GET /stats`

Returns headline business metrics read straight from SQLite — total revenue,
units, average order value, customer count, products below their reorder point,
revenue by month, revenue by region and top products. This powers the landing
dashboard. **No LLM call and no API key required**, so the dashboard renders
instantly even before a Groq key is configured.

```json
{
  "available": true,
  "total_revenue": 2225700.0,
  "total_units": 82544,
  "total_orders": 3800,
  "avg_order_value": 585.71,
  "low_stock_count": 2,
  "revenue_by_month": [{"month": "2025-09", "revenue": 74130.0, "units": 2743}],
  "revenue_by_region": [{"region": "North", "revenue": 852570.0, "units": 31544}],
  "top_products": [{"product": "Gadget X", "revenue": 665715.0, "units": 44381}]
}
```

When the database has not been seeded yet it returns
`{"available": false, "message": "..."}` instead of failing.

### `GET /health`

Returns `{"status": "ok"}` — use to verify the server is running.

---

## 🎛️ Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Groq model name |
| `API_URL` | `http://localhost:8000` | Backend URL used by Streamlit |
| `DB_PATH` | `db.sqlite` | Path to SQLite database file |
| `CHROMA_PATH` | `chroma_db` | Path to ChromaDB persistent storage |

---

## 🧪 Running Tests

```bash
pip install pytest
pytest -v
```

The suite covers the SQL security guardrail, markdown cleaning, LangGraph node
routing, and the dashboard statistics queries. **No API key or internet
connection is required** — every test runs offline in about a second.

---

## 🧩 Architecture Notes

### Decoupled Frontend/Backend

The Streamlit UI is a **pure thin client** — it only makes HTTP calls to FastAPI. All agent logic, LangGraph orchestration, DB access, and vector search live exclusively in the FastAPI backend. This means:

- You can test the entire BI system without any UI using `curl` or Postman.
- The Streamlit frontend can be swapped for a **React/Next.js** app without changing a single line of backend or agent code — FastAPI is the stable contract.

### Agent Safety

- The SQL Agent applies a **security guardrail** that blocks any generated query containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, or `TRUNCATE`.
- The RAG Agent uses **strict context grounding** — it instructs the LLM to only use retrieved chunks and explicitly say so if the answer isn't in the documents.

### Dashboard & Charts

The dashboard reads `GET /stats`, which runs plain parameter-free `SELECT`s — no
LLM, no API key — so it renders immediately on page load.

Chart colours come from a colourblind-safe categorical palette stepped for a dark
surface, and were validated rather than eyeballed: the two series hues separate by
ΔE 26.8 under protanopia (target ≥ 8) and 31.8 for normal vision (floor ≥ 15), both
clearing 3:1 contrast against the chart surface. Series identity is never carried by
colour alone — a legend is always present for two or more series, and bar values are
directly labelled.

The forecast chart draws the confidence interval (`yhat_lower` / `yhat_upper`) that
the model already computes as a shaded band, so the widening uncertainty over the
prediction horizon is visible rather than discarded.

### Error Handling

- Each agent wraps its logic in `try/except`. If an agent fails, the Synthesizer still produces a partial answer from whichever agents succeeded.
- The LangGraph `errors` field accumulates warnings from all branches without crashing the graph.

---

## 🔮 Sample Queries

| Query | Agents Used |
|---|---|
| `"Total revenue by region last month?"` | SQL |
| `"What is our return policy?"` | RAG |
| `"Forecast Widget A sales for next 30 days"` | Forecast |
| `"Which products are below reorder point?"` | SQL |
| `"Shipping time and return windows for bulk orders?"` | RAG |
| `"How is revenue trending and what does Q2 report say?"` | SQL + RAG |
| `"Predict revenue trend based on historical data"` | SQL + Forecast |
