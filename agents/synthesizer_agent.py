from typing import Dict, Any, Optional
from utils.llm_client import llm_client

SYSTEM_PROMPT = """You are a master business intelligence synthesizer.
Combine the following agent outputs into one clear, well-organized answer
for the user. Resolve any redundancy. If agents disagree, note it.
Keep your response professional, structured, and easy to read.
Use bullet points and bold headers for readability.
"""

def run_synthesizer_agent(
    query: str,
    sql_explanation: Optional[str] = None,
    rag_explanation: Optional[str] = None,
    forecast_explanation: Optional[str] = None
) -> str:
    """
    Synthesizes answers from multiple sub-agents into a consolidated report.
    """
    outputs = []
    if sql_explanation:
        outputs.append(f"Structured Data (SQL Query Analysis):\n{sql_explanation}")
    if rag_explanation:
        outputs.append(f"Unstructured Documentation (RAG Retrieval):\n{rag_explanation}")
    if forecast_explanation:
        outputs.append(f"Time-Series Forecasting:\n{forecast_explanation}")
        
    outputs_str = "\n\n---\n\n".join(outputs)
    
    prompt = f"""Original question: {query}

Agent outputs:
{outputs_str}
"""
    
    try:
        synthesized_answer = llm_client.query(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT
        )
        return synthesized_answer
    except Exception as e:
        print(f"Synthesizer Agent error: {e}")
        # Return simple join of answers as fallback
        fallback_msg = "Synthesizer failed to generate output. Here are raw agent results:\n\n"
        if sql_explanation:
            fallback_msg += f"**Database Analysis:** {sql_explanation}\n\n"
        if rag_explanation:
            fallback_msg += f"**Doc Retrieval:** {rag_explanation}\n\n"
        if forecast_explanation:
            fallback_msg += f"**Forecast:** {forecast_explanation}\n\n"
        return fallback_msg
