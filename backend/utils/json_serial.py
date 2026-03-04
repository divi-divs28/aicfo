"""
JSON serialization helpers - convert date/datetime to strings for JSON serialization.
"""
from datetime import date, datetime
from typing import Any, List, Dict


def _to_json_serializable(value: Any) -> Any:
    """Convert a single value to JSON-serializable form (date/datetime -> ISO string)."""
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_json_serializable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_json_serializable(v) for k, v in value.items()}
    return value


def sanitize_chat_response(response: Any) -> None:
    """
    Mutate a ChatResponse (or similar) in place so all date/datetime in
    tables (rows, full_data), charts (data), and kpi_cards (value) are
    converted to ISO strings. Fixes "Object of type date is not JSON serializable".
    """
    if response is None:
        return
    # Tables: rows and full_data
    if hasattr(response, "tables") and response.tables:
        for table in response.tables:
            if hasattr(table, "rows") and table.rows is not None:
                table.rows = [_to_json_serializable(row) for row in table.rows]
            if hasattr(table, "full_data") and table.full_data is not None:
                table.full_data = [_to_json_serializable(row) for row in table.full_data]
    # Charts: data (list of dicts)
    if hasattr(response, "charts") and response.charts:
        for chart in response.charts:
            if hasattr(chart, "data") and chart.data is not None:
                chart.data = [_to_json_serializable(d) for d in chart.data]
    # KPI cards: value
    if hasattr(response, "kpi_cards") and response.kpi_cards:
        for kpi in response.kpi_cards:
            if hasattr(kpi, "value"):
                kpi.value = _to_json_serializable(kpi.value)
