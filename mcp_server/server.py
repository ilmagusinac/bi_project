from datetime import date, datetime
from decimal import Decimal
from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    from . import database
except ImportError:
    import database


mcp = FastMCP("olist-bi-postgres")


METRICS: dict[str, dict[str, str]] = {
    "total_revenue": {
        "formula": "SUM(fact_order_items.total_item_value)",
        "description": "Total item value including product revenue and freight.",
        "grain": "Order item",
    },
    "product_revenue": {
        "formula": "SUM(fact_order_items.product_revenue)",
        "description": "Revenue from product price before freight.",
        "grain": "Order item",
    },
    "freight_revenue": {
        "formula": "SUM(fact_order_items.freight_value)",
        "description": "Total freight value charged on order items.",
        "grain": "Order item",
    },
    "total_orders": {
        "formula": "COUNT(DISTINCT fact_order_items.order_id)",
        "description": "Distinct Olist orders represented in the fact table.",
        "grain": "Order",
    },
    "average_order_value": {
        "formula": "SUM(fact_order_items.product_revenue) / COUNT(DISTINCT fact_order_items.order_id)",
        "description": "Average product revenue per distinct order.",
        "grain": "Order",
    },
    "late_delivery_rate": {
        "formula": "AVG(CASE WHEN fact_order_items.is_late THEN 1.0 ELSE 0.0 END)",
        "description": "Share of delivered order items delivered after the estimated delivery date.",
        "grain": "Order item",
    },
    "average_review_score": {
        "formula": "AVG(dim_review.review_score)",
        "description": "Average review score from the canonical review joined to each fact row.",
        "grain": "Order review",
    },
    "average_delivery_days": {
        "formula": "AVG(fact_order_items.delivery_days)",
        "description": "Average days between purchase timestamp and customer delivery timestamp.",
        "grain": "Order item",
    },
    "freight_ratio": {
        "formula": "SUM(fact_order_items.freight_value) / NULLIF(SUM(fact_order_items.total_item_value), 0)",
        "description": "Freight as a share of total item value.",
        "grain": "Order item",
    },
}


@mcp.tool()
def list_tables() -> list[dict[str, Any]]:
    """List supported BI warehouse tables in the public schema."""
    return _json_ready(database.list_tables())


@mcp.tool()
def describe_table(table_name: str) -> dict[str, Any]:
    """Describe columns and constraints for one supported warehouse table."""
    return _json_ready(database.describe_table(table_name))


@mcp.tool()
def get_schema() -> dict[str, Any]:
    """Return supported warehouse tables, columns, and foreign keys."""
    return _json_ready(database.get_schema())


@mcp.tool()
def get_foreign_keys() -> list[dict[str, Any]]:
    """List warehouse foreign key relationships."""
    return _json_ready(database.get_foreign_keys())


@mcp.tool()
def list_metrics() -> list[dict[str, str]]:
    """List supported BI metric definitions."""
    return [
        {
            "metric_name": name,
            "formula": metric["formula"],
            "description": metric["description"],
            "grain": metric["grain"],
        }
        for name, metric in sorted(METRICS.items())
    ]


@mcp.tool()
def explain_metric(metric_name: str) -> dict[str, str]:
    """Explain one BI metric by name."""
    normalized_name = metric_name.strip().lower()
    if normalized_name not in METRICS:
        valid_metrics = ", ".join(sorted(METRICS))
        raise ValueError(f"Unknown metric '{metric_name}'. Valid metrics: {valid_metrics}")

    metric = METRICS[normalized_name]
    return {
        "metric_name": normalized_name,
        "formula": metric["formula"],
        "description": metric["description"],
        "grain": metric["grain"],
    }


@mcp.tool()
def run_readonly_sql(sql_query: str) -> list[dict[str, Any]]:
    """Run a single read-only SELECT query. LIMIT 100 is added when omitted."""
    return _json_ready(database.run_readonly_sql(sql_query))


def _json_ready(value: Any) -> Any:
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


if __name__ == "__main__":
    mcp.run()
