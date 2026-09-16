import sqlite3
import os
import re
from typing import Dict, Any, List, Tuple
from utils.llm_client import llm_client
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "db.sqlite")

def get_db_schema() -> str:
    """
    Connects to the SQLite database, inspects table structure and retrieves
    sample rows to build a comprehensive schema context for the LLM.
    """
    if not os.path.exists(DB_PATH):
        return "Database file not found. Ensure seed_db.py has been run."
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_parts = []
        for table in tables:
            # Get CREATE TABLE statement
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            create_sql = cursor.fetchone()[0]
            
            # Get table columns
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Get sample rows
            cursor.execute(f"SELECT * FROM {table} LIMIT 3")
            sample_rows = cursor.fetchall()
            
            sample_data = []
            for row in sample_rows:
                sample_data.append(dict(zip(columns, row)))
            
            sample_str = "\n".join([str(s) for s in sample_data])
            schema_parts.append(f"Table Schema for '{table}':\n{create_sql}\nSample Rows:\n{sample_str}\n")
            
        return "\n".join(schema_parts)
    except Exception as e:
        return f"Error reading database schema: {str(e)}"
    finally:
        conn.close()

def execute_query(sql: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Executes the SQLite query and returns results as list of dicts along with columns.
    """
    conn = sqlite3.connect(DB_PATH)
    # Configure row factory to return dict-like rows
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Convert sqlite3.Row objects to standard python dicts
        result_rows = [dict(row) for row in rows]
        return result_rows, columns
    finally:
        conn.close()

def clean_sql(sql_str: str) -> str:
    """
    Cleans markdown formatting and whitespace from LLM-generated SQL query.
    """
    # Remove code block markers
    cleaned = re.sub(r"```sql\s*", "", sql_str, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    return cleaned

def contains_unsafe_sql(sql: str) -> bool:
    """
    Security Guardrail: Rejects write, edit, drop, alter, or dangerous commands.
    """
    sql_upper = sql.upper()
    # Check for forbidden keywords as whole words or starting actions
    forbidden_patterns = [
        r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b", 
        r"\bALTER\b", r"\bCREATE\b", r"\bREPLACE\b", r"\bTRUNCATE\b"
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, sql_upper):
            return True
    return False

def run_sql_agent(query: str) -> Dict[str, Any]:
    """
    Orchestrates the SQL Agent flow: Schema Retrieval -> SQL Generation ->
    Guardrail -> Execution (with Self-Correction) -> Explanation.
    """
    schema = get_db_schema()
    
    gen_system_prompt = f"""You are a SQL expert. Convert the user's question into a valid SQLite query.
Schema:
{schema}

Rules:
- SELECT statements only, never write/alter/delete
- Use exact table/column names from the schema
- If ambiguous, make a reasonable assumption and state it in a SQL comment
Return ONLY the SQL query. Do not wrap in markdown or explain.
"""
    
    # Step 1: Generate SQL
    try:
        generated_raw = llm_client.query(
            prompt=f"Question: {query}",
            system_prompt=gen_system_prompt
        )
        sql = clean_sql(generated_raw)
        
        # Step 2: Security Guardrail Check
        if contains_unsafe_sql(sql):
            return {
                "query": query,
                "sql_query": sql,
                "sql_rows": [],
                "explanation": "Security Error: The generated query contained unauthorized write/modify statements."
            }
            
        # Step 3: Execution and Self-Correction
        try:
            rows, columns = execute_query(sql)
        except Exception as exec_err:
            print(f"SQL execution failed: {exec_err}. Attempting self-correction...")
            # Attempt single-shot self-correction
            correct_prompt = f"""The SQL query:
{sql}
failed with the following error:
{str(exec_err)}

Please inspect the schema and correct this query. Return ONLY the corrected SQL query. Do not wrap it in markdown.
"""
            corrected_raw = llm_client.query(
                prompt=correct_prompt,
                system_prompt=gen_system_prompt
            )
            sql = clean_sql(corrected_raw)
            
            # Guardrail check again
            if contains_unsafe_sql(sql):
                return {
                    "query": query,
                    "sql_query": sql,
                    "sql_rows": [],
                    "explanation": "Security Error: The corrected query contained unauthorized write/modify statements."
                }
                
            # Try running again
            rows, columns = execute_query(sql)
            
        # Step 4: Explanation
        explain_system_prompt = f"Given this query result: {str(rows)}\nAnswer the original question in plain business language: {query}"
        explanation = llm_client.query(
            prompt="Generate a plain business explanation of the results.",
            system_prompt=explain_system_prompt
        )
        
        return {
            "query": query,
            "sql_query": sql,
            "sql_rows": rows,
            "explanation": explanation
        }
        
    except Exception as e:
        print(f"SQL Agent error: {e}")
        return {
            "query": query,
            "sql_query": "",
            "sql_rows": [],
            "explanation": f"SQL Agent was unable to process the query. Error: {str(e)}"
        }

if __name__ == "__main__":
    # Test SQL Agent
    print("Testing SQL Agent...")
    print(get_db_schema())
    test_result = run_sql_agent("What is the total units sold for Widget A?")
    print("SQL Query generated:", test_result["sql_query"])
    print("SQL Rows retrieved:", test_result["sql_rows"])
    print("Explanation:", test_result["explanation"])
