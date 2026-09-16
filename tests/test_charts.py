"""
Tests for the frontend chart builders.

These import streamlit_app, which is safe: every Streamlit call at module level
is display-only, and the one network call (fetch_stats) is wrapped so it returns
an "unavailable" dict instead of raising when no backend is running.
"""

import altair as alt
import pytest

import streamlit_app as ui


# --- Formatting helpers ----------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        (2_226_180, "$2.23M"),
        (45_100, "$45.1K"),
        (912, "$912"),
        (0, "$0"),
        (None, "—"),
        ("not a number", "—"),
    ],
)
def test_fmt_money(value, expected):
    assert ui.fmt_money(value) == expected


def test_fmt_int_adds_separators():
    assert ui.fmt_int(3805) == "3,805"
    assert ui.fmt_int(None) == "—"


# --- Charts return None instead of crashing on bad input -------------------

def test_charts_handle_empty_input():
    assert ui.revenue_trend_chart([]) is None
    assert ui.region_chart([]) is None
    assert ui.top_products_chart([]) is None
    assert ui.forecast_chart([], []) is None
    assert ui.sql_auto_chart([]) is None


def test_revenue_trend_handles_missing_columns():
    assert ui.revenue_trend_chart([{"wrong": 1}, {"wrong": 2}]) is None


# --- Dashboard charts build ------------------------------------------------

def test_revenue_trend_chart_builds():
    rows = [
        {"month": "2026-01", "revenue": 150.0, "units": 6},
        {"month": "2026-02", "revenue": 350.0, "units": 15},
    ]
    chart = ui.revenue_trend_chart(rows)
    assert chart is not None
    chart.to_dict()  # raises if the spec is invalid


def test_region_chart_builds():
    rows = [
        {"region": "North", "revenue": 350.0},
        {"region": "West", "revenue": 100.0},
        {"region": "South", "revenue": 50.0},
    ]
    chart = ui.region_chart(rows)
    assert chart is not None
    chart.to_dict()


def test_top_products_chart_builds():
    rows = [
        {"product": "Widget A", "revenue": 350.0, "units": 14},
        {"product": "Widget B", "revenue": 150.0, "units": 7},
    ]
    chart = ui.top_products_chart(rows)
    assert chart is not None
    chart.to_dict()


# --- Forecast chart --------------------------------------------------------

def test_forecast_chart_draws_confidence_band():
    """yhat_lower / yhat_upper must reach the chart, not be dropped."""
    historical = [{"ds": "2026-01-01", "y": 100}, {"ds": "2026-01-02", "y": 110}]
    predicted = [
        {"ds": "2026-01-03", "yhat": 120, "yhat_lower": 100, "yhat_upper": 140},
        {"ds": "2026-01-04", "yhat": 130, "yhat_lower": 105, "yhat_upper": 155},
    ]
    chart = ui.forecast_chart(historical, predicted)
    assert chart is not None
    spec = chart.to_dict()
    marks = [layer.get("mark") for layer in spec["layer"]]
    mark_types = {m["type"] if isinstance(m, dict) else m for m in marks}
    assert "area" in mark_types, "confidence band area layer is missing"
    assert "line" in mark_types


def test_forecast_chart_without_band_still_builds():
    """Older payloads with no interval columns must not crash the chart."""
    historical = [{"ds": "2026-01-01", "y": 100}, {"ds": "2026-01-02", "y": 110}]
    predicted = [{"ds": "2026-01-03", "yhat": 120}]
    chart = ui.forecast_chart(historical, predicted)
    assert chart is not None
    chart.to_dict()


def test_forecast_chart_uses_two_distinct_series_colors():
    historical = [{"ds": "2026-01-01", "y": 100}]
    predicted = [{"ds": "2026-01-02", "yhat": 120, "yhat_lower": 90, "yhat_upper": 150}]
    chart = ui.forecast_chart(historical, predicted)
    spec = chart.to_dict()
    colors = None
    for layer in spec["layer"]:
        color_enc = layer.get("encoding", {}).get("color")
        if color_enc and "scale" in color_enc:
            colors = color_enc["scale"]["range"]
    assert colors == [ui.SERIES_1, ui.SERIES_2]
    assert ui.SERIES_1 != ui.SERIES_2


# --- SQL auto-chart heuristics ---------------------------------------------

def test_sql_auto_chart_builds_for_label_plus_number():
    rows = [
        {"region": "North", "total": 350.0},
        {"region": "West", "total": 100.0},
        {"region": "South", "total": 50.0},
    ]
    chart = ui.sql_auto_chart(rows)
    assert chart is not None
    chart.to_dict()


def test_sql_auto_chart_skips_single_row():
    assert ui.sql_auto_chart([{"region": "North", "total": 350.0}]) is None


def test_sql_auto_chart_skips_three_columns():
    rows = [
        {"region": "North", "total": 350.0, "units": 14},
        {"region": "West", "total": 100.0, "units": 5},
    ]
    assert ui.sql_auto_chart(rows) is None


def test_sql_auto_chart_skips_two_numeric_columns():
    rows = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    assert ui.sql_auto_chart(rows) is None


def test_sql_auto_chart_skips_duplicate_labels():
    rows = [
        {"region": "North", "total": 350.0},
        {"region": "North", "total": 100.0},
    ]
    assert ui.sql_auto_chart(rows) is None


def test_sql_auto_chart_skips_too_many_rows():
    rows = [{"label": f"item {i}", "value": i} for i in range(30)]
    assert ui.sql_auto_chart(rows) is None


# --- Chart styling contract ------------------------------------------------

def test_charts_are_altair_objects():
    rows = [{"region": "North", "revenue": 1.0}, {"region": "West", "revenue": 2.0}]
    assert isinstance(ui.region_chart(rows), alt.TopLevelMixin)


# --- Streamlit width compatibility -----------------------------------------

def test_stretch_returns_a_supported_keyword():
    """
    Whichever Streamlit is installed, stretch() must return a keyword that the
    widget actually accepts — never one it would reject.
    """
    import inspect

    import streamlit as st

    for name in ("altair_chart", "dataframe", "button"):
        kwargs = ui.stretch(name)
        assert len(kwargs) == 1
        key = next(iter(kwargs))
        assert key in {"width", "use_container_width"}
        params = inspect.signature(getattr(st, name)).parameters
        assert key in params, f"st.{name} does not accept {key}"


def test_stretch_value_matches_key():
    kwargs = ui.stretch("altair_chart")
    if "width" in kwargs:
        assert kwargs["width"] == "stretch"
    else:
        assert kwargs["use_container_width"] is True


def test_forecast_chart_shares_one_y_axis():
    """
    Both layers must encode the SAME y field. Different field names make
    Vega-Lite draw two y-axes or drop the axis entirely — never dual-axis.
    """
    historical = [{"ds": "2026-01-01", "y": 100}, {"ds": "2026-01-02", "y": 110}]
    predicted = [
        {"ds": "2026-01-03", "yhat": 120, "yhat_lower": 100, "yhat_upper": 140},
        {"ds": "2026-01-04", "yhat": 130, "yhat_lower": 105, "yhat_upper": 155},
    ]
    spec = ui.forecast_chart(historical, predicted).to_dict()
    y_fields = {
        layer["encoding"]["y"]["field"]
        for layer in spec["layer"]
        if layer.get("encoding", {}).get("y")
    }
    assert y_fields == {"value"}, f"layers disagree on the y field: {y_fields}"
