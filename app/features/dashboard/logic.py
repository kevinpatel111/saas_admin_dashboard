"""Business logic and data transformations for dashboard analytics."""

from __future__ import annotations

from typing import Any


def calculate_dashboard_stats(
    total_users: int,
    active_users: int,
    total_products: int,
    total_categories: int,
    low_stock_count: int,
) -> dict[str, int]:
    """Calculate and aggregate summary statistics for the dashboard cards.

    Returns:
        dict[str, int]: Summary metrics dict.
    """
    inactive_users = max(0, total_users - active_users)
    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "total_products": total_products,
        "total_categories": total_categories,
        "low_stock_count": low_stock_count,
    }


def format_chart_data(
    monthly_data: list[tuple[str, int]],
    category_data: list[tuple[str, int]],
) -> dict[str, Any]:
    """Format monthly product trends and category distribution for Chart.js consumption.

    Args:
        monthly_data: List of tuples (e.g. [("2026-05", 10), ("2026-06", 15)])
        category_data: List of tuples (e.g. [("Electronics", 20), ("Apparel", 12)])

    Returns:
        dict[str, Any]: Chart.js datasets structure.
    """
    monthly_labels = [m[0] for m in monthly_data]
    monthly_values = [m[1] for m in monthly_data]

    category_labels = [c[0] for c in category_data]
    category_values = [c[1] for c in category_data]

    return {
        "monthly_activity": {
            "labels": monthly_labels,
            "datasets": [
                {
                    "label": "New Products",
                    "data": monthly_values,
                    "borderColor": "#4f46e5",
                    "backgroundColor": "rgba(79, 70, 229, 0.1)",
                    "tension": 0.3,
                    "fill": True,
                }
            ],
        },
        "category_distribution": {
            "labels": category_labels,
            "datasets": [
                {
                    "label": "Products by Category",
                    "data": category_values,
                    "backgroundColor": [
                        "#4f46e5",
                        "#06b6d4",
                        "#10b981",
                        "#f59e0b",
                        "#ef4444",
                        "#8b5cf6",
                        "#ec4899",
                        "#6b7280",
                    ],
                }
            ],
        },
    }
