"""Call functions for the dashboard orchestrating repositories and logic across features."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.features.categories.repository import count_categories
from app.features.dashboard import logic
from app.features.products.models import Product
from app.features.products.repository import (
    count_low_stock_products,
    count_products,
    get_low_stock_products,
    get_monthly_product_counts,
    get_products_by_category_count,
)
from app.features.users.models import User
from app.features.users.repository import count_users

settings = get_settings()


async def get_dashboard_stats_call(db: AsyncSession) -> dict[str, int]:
    """Aggregate high-level SaaS dashboard statistics."""
    total_users = await count_users(db, active_only=False)
    active_users = await count_users(db, active_only=True)
    total_products = await count_products(db)
    total_categories = await count_categories(db)
    low_stock_count = await count_low_stock_products(
        db, threshold=settings.LOW_STOCK_THRESHOLD
    )

    return logic.calculate_dashboard_stats(
        total_users=total_users,
        active_users=active_users,
        total_products=total_products,
        total_categories=total_categories,
        low_stock_count=low_stock_count,
    )


async def get_chart_data_call(db: AsyncSession) -> dict[str, Any]:
    """Fetch time-series monthly activity and category distribution for charts."""
    monthly_data = await get_monthly_product_counts(db, months=6)
    category_data = await get_products_by_category_count(db)
    return logic.format_chart_data(monthly_data, category_data)


async def get_recent_activity_call(db: AsyncSession) -> dict[str, list[dict[str, Any]]]:
    """Fetch recent users and products (last 10 of each, sorted by created_at desc).

    Returns:
        dict: {"recent_users": [...], "recent_products": [...]}
    """
    # 10 most recent users
    user_stmt = select(User).order_by(User.created_at.desc()).limit(10)
    user_result = await db.execute(user_stmt)
    users = list(user_result.scalars().all())

    # 10 most recent products
    prod_stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .order_by(Product.created_at.desc())
        .limit(10)
    )
    prod_result = await db.execute(prod_stmt)
    products = list(prod_result.scalars().all())

    recent_users = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]

    recent_products = [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "price": p.price,
            "stock_quantity": p.stock_quantity,
            "category_name": p.category.name if p.category else "Uncategorized",
            "status": p.status,
            "created_at": p.created_at,
        }
        for p in products
    ]

    return {
        "recent_users": recent_users,
        "recent_products": recent_products,
    }


async def get_dashboard_summary_call(db: AsyncSession) -> dict[str, Any]:
    """Comprehensive dashboard payload combining stats, charts, recent activity, and low stock items."""
    stats = await get_dashboard_stats_call(db)
    charts = await get_chart_data_call(db)
    activity = await get_recent_activity_call(db)
    low_stock_products = await get_low_stock_products(
        db, threshold=settings.LOW_STOCK_THRESHOLD, limit=5
    )

    return {
        "stats": stats,
        "charts": charts,
        "recent_users": activity["recent_users"],
        "recent_products": activity["recent_products"],
        "low_stock_products": low_stock_products,
    }
