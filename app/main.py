"""
FastAPI backend for the Multi-Agent Business Intelligence System.

Single endpoint:
  POST /query
    Request:  { "query": str }
    Response: {
        "final_answer": str,
        "agents_used": List[str],
        "routing_reasoning": str,
        "sql_result": Optional[dict],
        "rag_result": Optional[dict],
        "forecast_result": Optional[dict],
        "errors": List[str]
    }

Start with:
    uvicorn app.main:app --reload --port 8000
"""

import os
import sys
import time

# Ensure the project root is on sys.path so relative imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.graph import graph, AgentState
from utils.db_stats import get_dashboard_stats

load_dotenv()

app = FastAPI(
    title="Multi-Agent Business Intelligence API",
    description=(
        "Orchestrates SQL, RAG, and Forecasting agents via LangGraph "
        "to answer business intelligence queries."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — allow Streamlit (and any future frontend) to call this backend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    final_answer: str
    agents_used: list
    routing_reasoning: str
    sql_result: dict | None = None
    rag_result: dict | None = None
    forecast_result: dict | None = None
    errors: list = []
    elapsed_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Multi-Agent BI API is running."}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dashboard statistics — powers the landing dashboard in the Streamlit UI
# ---------------------------------------------------------------------------

@app.get("/stats", tags=["Dashboard"])
async def stats_endpoint():
    """
    Returns headline business metrics straight from SQLite.

    No LLM call and no API key needed, so the dashboard renders instantly when
    the UI loads.
    """
    try:
        return get_dashboard_stats()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read dashboard statistics: {str(e)}",
        )


# ---------------------------------------------------------------------------
# Main query endpoint
# ---------------------------------------------------------------------------

@app.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_endpoint(request: QueryRequest):
    """
    Accepts a natural-language business query, runs it through the LangGraph
    multi-agent pipeline, and returns a synthesized answer along with the
    raw outputs of each sub-agent that was invoked.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    # Validate Groq key is present (fast-fail before the graph runs)
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY is not configured on the server.",
        )

    # Build initial state
    initial_state: AgentState = {
        "query": request.query.strip(),
        "selected_agents": [],
        "routing_reasoning": "",
        "sql_result": None,
        "rag_result": None,
        "forecast_result": None,
        "final_answer": None,
        "errors": [],
    }

    started = time.perf_counter()
    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Graph execution failed: {str(e)}",
        )

    return QueryResponse(
        final_answer=final_state.get("final_answer") or "No answer was produced.",
        agents_used=final_state.get("selected_agents", []),
        routing_reasoning=final_state.get("routing_reasoning", ""),
        sql_result=final_state.get("sql_result"),
        rag_result=final_state.get("rag_result"),
        forecast_result=final_state.get("forecast_result"),
        errors=final_state.get("errors", []),
        elapsed_seconds=round(time.perf_counter() - started, 2),
    )
