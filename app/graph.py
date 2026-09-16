"""
LangGraph workflow definition for the Multi-Agent Business Intelligence System.

Graph flow:
  START -> router_node -> [sql_node, rag_node, forecast_node] (parallel, conditional) -> synthesizer_node -> END

IMPORTANT: Each node returns ONLY the keys it modifies.
LangGraph merges partial state updates automatically. Returning {**state, ...} causes
INVALID_CONCURRENT_GRAPH_UPDATE errors when multiple branches run in parallel.
"""

import operator
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END

from agents.router_agent import route_query
from agents.sql_agent import run_sql_agent
from agents.rag_agent import run_rag_agent
from agents.forecast_agent import run_forecast_agent
from agents.synthesizer_agent import run_synthesizer_agent


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    query: str                              # Set once by the caller, never written by nodes
    selected_agents: List[str]              # Written by router_node only
    routing_reasoning: str                  # Written by router_node only
    sql_result: Optional[dict]              # Written by sql_node only
    rag_result: Optional[dict]              # Written by rag_node only
    forecast_result: Optional[dict]         # Written by forecast_node only
    final_answer: Optional[str]             # Written by synthesizer_node only
    errors: Annotated[List[str], operator.add]  # Accumulates from all branches safely


# ---------------------------------------------------------------------------
# Node functions  — each returns ONLY the keys it owns
# ---------------------------------------------------------------------------

def router_node(state: AgentState) -> dict:
    """Classifies the query and sets selected_agents."""
    try:
        result = route_query(state["query"])
        return {
            "selected_agents": result.get("agents", ["sql"]),
            "routing_reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        return {
            "selected_agents": ["sql"],
            "routing_reasoning": "",
            "errors": [f"Router error: {str(e)}"],
        }


def sql_node(state: AgentState) -> dict:
    """Runs the SQL agent if 'sql' was selected by the router."""
    if "sql" not in state.get("selected_agents", []):
        return {}   # Nothing to do — return empty update
    try:
        result = run_sql_agent(state["query"])
        return {"sql_result": result}
    except Exception as e:
        return {
            "sql_result": {
                "query": state["query"],
                "sql_query": "",
                "sql_rows": [],
                "explanation": f"SQL agent failed: {str(e)}",
            },
            "errors": [f"SQL node error: {str(e)}"],
        }


def rag_node(state: AgentState) -> dict:
    """Runs the RAG agent if 'rag' was selected by the router."""
    if "rag" not in state.get("selected_agents", []):
        return {}
    try:
        result = run_rag_agent(state["query"])
        return {"rag_result": result}
    except Exception as e:
        return {
            "rag_result": {
                "query": state["query"],
                "retrieved_chunks": [],
                "explanation": f"RAG agent failed: {str(e)}",
            },
            "errors": [f"RAG node error: {str(e)}"],
        }


def forecast_node(state: AgentState) -> dict:
    """Runs the Forecast agent if 'forecast' was selected by the router."""
    if "forecast" not in state.get("selected_agents", []):
        return {}
    try:
        result = run_forecast_agent(state["query"])
        return {"forecast_result": result}
    except Exception as e:
        return {
            "forecast_result": {
                "query": state["query"],
                "historical_data": [],
                "forecast_data": [],
                "model_used": "None",
                "explanation": f"Forecast agent failed: {str(e)}",
            },
            "errors": [f"Forecast node error: {str(e)}"],
        }


def synthesizer_node(state: AgentState) -> dict:
    """Combines agent outputs into a final coherent answer."""
    try:
        sql_exp = state.get("sql_result", {}).get("explanation") if state.get("sql_result") else None
        rag_exp = state.get("rag_result", {}).get("explanation") if state.get("rag_result") else None
        forecast_exp = state.get("forecast_result", {}).get("explanation") if state.get("forecast_result") else None

        final = run_synthesizer_agent(
            query=state["query"],
            sql_explanation=sql_exp,
            rag_explanation=rag_exp,
            forecast_explanation=forecast_exp,
        )
        return {"final_answer": final}
    except Exception as e:
        # Graceful degradation — join whatever is available
        parts = []
        if state.get("sql_result"):
            parts.append(state["sql_result"].get("explanation", ""))
        if state.get("rag_result"):
            parts.append(state["rag_result"].get("explanation", ""))
        if state.get("forecast_result"):
            parts.append(state["forecast_result"].get("explanation", ""))
        return {
            "final_answer": "\n\n".join(parts) if parts else "Unable to produce an answer.",
            "errors": [f"Synthesizer error: {str(e)}"],
        }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph():
    """Builds and compiles the LangGraph state machine."""
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("router", router_node)
    builder.add_node("sql", sql_node)
    builder.add_node("rag", rag_node)
    builder.add_node("forecast", forecast_node)
    builder.add_node("synthesizer", synthesizer_node)

    # Entry point
    builder.set_entry_point("router")

    # Router fans out to all three agent nodes in parallel
    # (Each node self-filters via selected_agents and returns {} if not needed)
    builder.add_edge("router", "sql")
    builder.add_edge("router", "rag")
    builder.add_edge("router", "forecast")

    # All three agent nodes converge at the synthesizer
    builder.add_edge("sql", "synthesizer")
    builder.add_edge("rag", "synthesizer")
    builder.add_edge("forecast", "synthesizer")

    # Synthesizer -> END
    builder.add_edge("synthesizer", END)

    return builder.compile()


# Compiled graph singleton
graph = build_graph()
