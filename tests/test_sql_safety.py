"""Tests for the SQL Agent security guardrail and query cleaning."""

from agents.sql_agent import clean_sql, contains_unsafe_sql


# --- Guardrail must BLOCK dangerous queries -------------------------------

def test_blocks_drop_table():
    assert contains_unsafe_sql("DROP TABLE sales") is True


def test_blocks_delete():
    assert contains_unsafe_sql("DELETE FROM sales WHERE id = 1") is True


def test_blocks_insert():
    assert contains_unsafe_sql("INSERT INTO sales VALUES (1)") is True


def test_blocks_update():
    assert contains_unsafe_sql("UPDATE sales SET revenue = 0") is True


def test_blocks_lowercase_drop():
    """The guardrail must work even if the LLM writes in lowercase."""
    assert contains_unsafe_sql("drop table sales") is True


# --- Guardrail must ALLOW safe queries ------------------------------------

def test_allows_simple_select():
    assert contains_unsafe_sql("SELECT * FROM sales") is False


def test_allows_aggregate_select():
    sql = "SELECT region, SUM(revenue) FROM sales GROUP BY region"
    assert contains_unsafe_sql(sql) is False


# --- clean_sql must strip markdown from LLM output ------------------------

def test_clean_sql_removes_markdown_block():
    assert clean_sql("```sql\nSELECT 1\n```") == "SELECT 1"


def test_clean_sql_leaves_plain_sql_unchanged():
    assert clean_sql("SELECT * FROM sales") == "SELECT * FROM sales"
