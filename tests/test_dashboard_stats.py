"""Tests for the dashboard statistics queries (no API key needed)."""

import os
import sqlite3

import pytest

from utils.db_stats import get_dashboard_stats


@pytest.fixture
def sample_db(tmp_path):
    """Builds a tiny database with known numbers so the maths is checkable."""
    path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, product TEXT NOT NULL, region TEXT NOT NULL,
            revenue REAL NOT NULL, units INTEGER NOT NULL
        );
        CREATE TABLE inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT UNIQUE NOT NULL,
            stock_level INTEGER NOT NULL, reorder_point INTEGER NOT NULL
        );
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, segment TEXT NOT NULL, ltv REAL NOT NULL
        );

        INSERT INTO sales (date, product, region, revenue, units) VALUES
            ('2026-01-05', 'Widget A', 'North', 100.0, 4),
            ('2026-01-20', 'Widget B', 'South',  50.0, 2),
            ('2026-02-10', 'Widget A', 'North', 250.0, 10),
            ('2026-02-15', 'Widget B', 'West',  100.0, 5);

        INSERT INTO inventory (product, stock_level, reorder_point) VALUES
            ('Widget A', 10, 50),     -- below reorder point
            ('Widget B', 500, 40);    -- healthy

        INSERT INTO customers (name, segment, ltv) VALUES
            ('Acme', 'Enterprise', 1000.0),
            ('Globex', 'SMB', 500.0);
        """
    )
    conn.commit()
    conn.close()
    return str(path)


def test_reports_unavailable_when_db_missing(tmp_path):
    stats = get_dashboard_stats(str(tmp_path / "does_not_exist.sqlite"))
    assert stats["available"] is False
    assert "seed_db" in stats["message"]


def test_headline_totals(sample_db):
    stats = get_dashboard_stats(sample_db)
    assert stats["available"] is True
    assert stats["total_revenue"] == 500.0
    assert stats["total_units"] == 21
    assert stats["total_orders"] == 4
    assert stats["avg_order_value"] == 125.0


def test_customer_totals(sample_db):
    stats = get_dashboard_stats(sample_db)
    assert stats["customer_count"] == 2
    assert stats["total_ltv"] == 1500.0


def test_low_stock_detection(sample_db):
    """Only products at or below their reorder point should be flagged."""
    stats = get_dashboard_stats(sample_db)
    assert stats["low_stock_count"] == 1
    assert stats["low_stock"][0]["product"] == "Widget A"


def test_revenue_by_month_is_sorted(sample_db):
    stats = get_dashboard_stats(sample_db)
    months = [row["month"] for row in stats["revenue_by_month"]]
    assert months == ["2026-01", "2026-02"]
    assert stats["revenue_by_month"][0]["revenue"] == 150.0
    assert stats["revenue_by_month"][1]["revenue"] == 350.0


def test_revenue_by_region_ranked(sample_db):
    stats = get_dashboard_stats(sample_db)
    regions = [row["region"] for row in stats["revenue_by_region"]]
    assert regions == ["North", "West", "South"]


def test_top_product_is_highest_revenue(sample_db):
    stats = get_dashboard_stats(sample_db)
    assert stats["top_product"] == "Widget A"
    assert stats["top_products"][0]["revenue"] == 350.0


def test_date_range(sample_db):
    stats = get_dashboard_stats(sample_db)
    assert stats["first_date"] == "2026-01-05"
    assert stats["last_date"] == "2026-02-15"
