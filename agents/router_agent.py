import json
from typing import List, Dict, Any
from utils.llm_client import llm_client

SYSTEM_PROMPT = """You are a query router for a business intelligence system.
Classify the user's question into one or more categories: "sql", "rag", "forecast".
Rules:
- "sql" = needs structured data (sales, inventory, revenue, counts, comparisons)
- "rag" = needs unstructured docs (policies, reports, notes)
- "forecast" = needs future prediction based on historical trend
Return ONLY valid JSON: {"agents": ["sql"], "reasoning": "..."}
"""

def route_query(query: str) -> Dict[str, Any]:
    """
    Classifies the user's query and returns a dictionary with the selected agents and reasoning.
    """
    prompt = f"Question: {query}"
    
    try:
        response_text = llm_client.query(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True
        )
        
        result = json.loads(response_text)
        
        # Validate structure
        if "agents" not in result or not isinstance(result["agents"], list):
            result["agents"] = ["sql"]  # default fallback
        
        # Verify agents contains valid categories
        valid_categories = {"sql", "rag", "forecast"}
        result["agents"] = [a.lower() for a in result["agents"] if a.lower() in valid_categories]
        
        if not result["agents"]:
            result["agents"] = ["sql"]  # fallback if empty
            
        return result
        
    except Exception as e:
        print(f"Router Agent Error: {e}")
        # Return fallback on error
        return {
            "agents": ["sql", "rag"],
            "reasoning": f"Fallback selected due to routing error: {str(e)}"
        }

if __name__ == "__main__":
    # Test router
    test_queries = [
        "What was our total revenue last month?",
        "What is our policy on returning widgets?",
        "Can you forecast sales for Widget A next month?",
        "What are Widget B sales trends and when should we reorder standard orders?",
    ]
    for q in test_queries:
        print(f"Query: {q}")
        print(route_query(q))
        print("-" * 50)
