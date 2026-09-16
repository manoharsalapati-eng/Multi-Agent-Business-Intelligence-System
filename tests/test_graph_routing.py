"""Tests for LangGraph node routing logic (no API calls needed)."""

from app.graph import forecast_node, rag_node, sql_node


def test_sql_node_skipped_when_not_selected():
    state = {"query": "test", "selected_agents": ["rag"]}
    assert sql_node(state) == {}


def test_rag_node_skipped_when_not_selected():
    state = {"query": "test", "selected_agents": ["sql"]}
    assert rag_node(state) == {}


def test_forecast_node_skipped_when_not_selected():
    state = {"query": "test", "selected_agents": ["sql", "rag"]}
    assert forecast_node(state) == {}


def test_router_falls_back_when_api_key_missing(monkeypatch):
    """If Groq is unreachable, the router must still return valid agents."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from agents.router_agent import route_query

    result = route_query("What is our total revenue?")
    assert isinstance(result["agents"], list)
    assert len(result["agents"]) > 0
    for agent in result["agents"]:
        assert agent in {"sql", "rag", "forecast"}
