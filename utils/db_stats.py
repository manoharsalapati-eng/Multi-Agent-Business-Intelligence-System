"""
Read-only dashboard statistics for the Multi-Agent BI System.

These queries power the landing dashboard in the Streamlit UI. They are plain
parameter-free SELECTs against the seeded SQLite database — no LLM involved —
so the dashboard renders instantly and works without a Groq API key.

Every function degrades gracefully: if the database has not been seeded yet,
get_dashboard_stats() returns {"available": False} instead of raising.
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "db.sqlite")


def _rows(conn: sqlite3.Connection, sql: str) -> List[Dict[str, Any]]:
    """Runs a SELECT and returns the rows as plain dicts."""
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(sql)
    return [dict(row) for row in cursor.fetchall()]


def _one(conn: sqlite3.Connection, sql: str) -> Dict[str, Any]:
    """Runs a SELECT expected to return a single row; {} if there is none."""
    rows = _rows(conn, sql)
    return rows[0] if rows else {}


def get_dashboard_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Builds the full dashboard payload in one database connection.

    Returns a dict with "available": False when the database file is missing,
    so the frontend can show a "run seed_db.py first" message rather than an
    error page.
    """
    path = db_path or DB_PATH

    if not os.path.exists(path):
        return {
            "available": False,
            "message": (
                "Database not found. Run `python data/seed_db.py` to create it."
            ),
        }

    conn = sqlite3.connect(path)
    try:
        totals = _one(
            conn,
            """
            SELECT
                COALESCE(SUM(revenue), 0) AS total_revenue,
                COALESCE(SUM(units), 0)   AS total_units,
                COUNT(*)                  AS total_orders,
                MIN(date)                 AS first_date,
                MAX(date)                 AS last_date
            FROM sales
            """,
        )

        total_orders = totals.get("total_orders", 0) or 0
        total_revenue = totals.get("total_revenue", 0) or 0
        avg_order_value = (total_revenue / total_orders) if total_orders else 0

        customers = _one(
            conn,
            "SELECT COUNT(*) AS customer_count, COALESCE(SUM(ltv), 0) AS total_ltv "
            "FROM customers",
        )

        revenue_by_month = _rows(
            conn,
            """
            SELECT substr(date, 1, 7) AS month,
                   ROUND(SUM(revenue), 2) AS revenue,
                   SUM(units) AS units
            FROM sales
            GROUP BY month
            ORDER BY month
            """,
        )

        revenue_by_region = _rows(
            conn,
            """
            SELECT region, ROUND(SUM(revenue), 2) AS revenue, SUM(units) AS units
            FROM sales
            GROUP BY region
            ORDER BY revenue DESC
            """,
        )

        top_products = _rows(
            conn,
            """
            SELECT product, ROUND(SUM(revenue), 2) AS revenue, SUM(units) AS units
            FROM sales
            GROUP BY product
            ORDER BY revenue DESC
            LIMIT 5
            """,
        )

        low_stock = _rows(
            conn,
            """
            SELECT product, stock_level, reorder_point
            FROM inventory
            WHERE stock_level <= reorder_point
            ORDER BY stock_level ASC
            """,
        )

        return {
            "available": True,
            "total_revenue": round(total_revenue, 2),
            "total_units": totals.get("total_units", 0) or 0,
            "total_orders": total_orders,
            "avg_order_value": round(avg_order_value, 2),
            "customer_count": customers.get("customer_count", 0) or 0,
            "total_ltv": round(customers.get("total_ltv", 0) or 0, 2),
            "first_date": totals.get("first_date"),
            "last_date": totals.get("last_date"),
            "top_product": top_products[0]["product"] if top_products else None,
            "low_stock_count": len(low_stock),
            "low_stock": low_stock,
            "revenue_by_month": revenue_by_month,
            "revenue_by_region": revenue_by_region,
            "top_products": top_products,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import json

    print(json.dumps(get_dashboard_stats(), indent=2)[:1500])
