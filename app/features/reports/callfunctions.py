"""Call functions for reports and exports orchestrating queries and CSV formatting."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.products.models import Product
from app.features.reports import logic
from app.features.users.models import User


async def export_users_csv_call(
    db: AsyncSession,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[bool] = None,
) -> str:
    """Retrieve filtered users and serialize to safe CSV string.

    Headers: ID, Name, Email, Role, Status, Created At
    NOTE: Never exports sensitive fields like password_hash or auth tokens.
    """
    stmt = select(User).order_by(User.id.asc())

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                User.name.ilike(term),
                User.email.ilike(term),
            )
        )

    if role_filter and role_filter.strip():
        stmt = stmt.where(User.role == role_filter.strip().lower())

    if status_filter is not None:
        stmt = stmt.where(User.is_active == status_filter)

    result = await db.execute(stmt)
    users = result.scalars().all()

    headers = ["ID", "Name", "Email", "Role", "Status", "Created At"]
    rows = []
    for u in users:
        rows.append(
            [
                u.id,
                u.name,
                u.email,
                u.role,
                "Active" if u.is_active else "Inactive",
                u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else "",
            ]
        )

    return logic.generate_csv_content(headers=headers, rows=rows)


async def export_products_csv_call(
    db: AsyncSession,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> str:
    """Retrieve filtered products and serialize to safe CSV string.

    Headers: ID, Name, SKU, Price, Stock, Category, Status, Created At
    """
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .order_by(Product.id.asc())
    )

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.description.ilike(term),
            )
        )

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    if status_filter and status_filter.strip():
        stmt = stmt.where(Product.status == status_filter.strip().lower())

    result = await db.execute(stmt)
    products = result.scalars().all()

    headers = [
        "ID",
        "Name",
        "SKU",
        "Price",
        "Stock",
        "Category",
        "Status",
        "Created At",
    ]
    rows = []
    for p in products:
        category_name = p.category.name if p.category else "Uncategorized"
        rows.append(
            [
                p.id,
                p.name,
                p.sku,
                f"{p.price:.2f}" if p.price is not None else "0.00",
                p.stock_quantity,
                category_name,
                p.status.capitalize() if p.status else "",
                p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
            ]
        )

    return logic.generate_csv_content(headers=headers, rows=rows)
