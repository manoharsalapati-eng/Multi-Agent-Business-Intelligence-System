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
| **UI** | Streamlit — premium dark chat interface |

---

## 🚀 Quick Start
**Requirement:** Python 3.10 or higher

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
cd Multi-Agent-Business-Intelligence-System/
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
│   └── llm_client.py           # Shared Groq API wrapper (single place for model/key config)
├── streamlit_app.py            # Streamlit thin-client UI
├── requirements.txt
├── .env.example
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
  "errors": []
}
```

### `GET /health`

Returns `{"status": "ok"}` — use to verify the server is running.

---

## 🎛️ Configuration

All configuration is via environment variables in `.env`:

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `GPT-OSS 120B` | Groq model name |
| `API_URL` | `http://localhost:8000` | Backend URL used by Streamlit |
| `DB_PATH` | `db.sqlite` | Path to SQLite database file |
| `CHROMA_PATH` | `chroma_db` | Path to ChromaDB persistent storage |

---

## 🧩 Architecture Notes

### Decoupled Frontend/Backend

The Streamlit UI is a **pure thin client** — it only makes HTTP calls to FastAPI. All agent logic, LangGraph orchestration, DB access, and vector search live exclusively in the FastAPI backend. This means:

- You can test the entire BI system without any UI using `curl` or Postman.
- The Streamlit frontend can be swapped for a **React/Next.js** app without changing a single line of backend or agent code — FastAPI is the stable contract.

### Agent Safety

- The SQL Agent applies a **security guardrail** that blocks any generated query containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, or `TRUNCATE`.
- The RAG Agent uses **strict context grounding** — it instructs the LLM to only use retrieved chunks and explicitly say so if the answer isn't in the documents.

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
