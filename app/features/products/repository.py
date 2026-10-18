"""Product repository — database queries for product management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.categories.models import Category
from app.features.products.models import Product


async def get_products(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> tuple[list[Product], int]:
    """Fetch paginated, filtered, and sorted products with category eagerly loaded.

    Returns:
        tuple[list[Product], int]: (products_list, total_count)
    """
    stmt = select(Product).options(selectinload(Product.category))

    # 1. Search filter: name OR sku OR description (case-insensitive)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Product.name).like(term),
                func.lower(Product.sku).like(term),
                func.lower(Product.description).like(term),
            )
        )

    # 2. Category filter
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    # 3. Status filter
    if status_filter and status_filter.strip():
        stmt = stmt.where(Product.status == status_filter.strip().lower())

    # Count query before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0

    # 4. Sorting
    valid_sort_columns = {
        "id": Product.id,
        "name": Product.name,
        "sku": Product.sku,
        "price": Product.price,
        "stock_quantity": Product.stock_quantity,
        "status": Product.status,
        "created_at": Product.created_at,
        "updated_at": Product.updated_at,
    }
    sort_column = valid_sort_columns.get(sort_by.lower(), Product.id)

    if sort_order.lower() == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    # 5. Pagination
    safe_page = max(1, page)
    safe_per_page = max(1, per_page)
    offset = (safe_page - 1) * safe_per_page
    stmt = stmt.offset(offset).limit(safe_per_page)

    result = await db.execute(stmt)
    products = list(result.scalars().all())

    return products, total_count


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    """Fetch product by primary key ID with category eagerly loaded."""
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.id == product_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_product_by_sku(db: AsyncSession, sku: str) -> Product | None:
    """Fetch product by normalized SKU."""
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.sku == sku.strip().upper())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, data: dict) -> Product:
    """Insert a new product entity and refresh."""
    product = Product(**data)
    db.add(product)
    await db.flush()
    # Re-fetch with category loaded
    return await get_product_by_id(db, product.id)  # type: ignore[return-value]


async def update_product(db: AsyncSession, product: Product, data: dict) -> Product:
    """Update product attributes and refresh."""
    for key, value in data.items():
        setattr(product, key, value)
    await db.flush()
    return await get_product_by_id(db, product.id)  # type: ignore[return-value]


async def delete_product(db: AsyncSession, product: Product) -> None:
    """Delete a product entity."""
    await db.delete(product)
    await db.flush()


async def count_products(db: AsyncSession) -> int:
    """Count total products."""
    stmt = select(func.count()).select_from(Product)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def count_low_stock_products(db: AsyncSession, threshold: int) -> int:
    """Count products whose stock_quantity is less than or equal to threshold."""
    stmt = (
        select(func.count())
        .select_from(Product)
        .where(Product.stock_quantity <= threshold)
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_low_stock_products(
    db: AsyncSession, threshold: int, limit: int = 5
) -> list[Product]:
    """Retrieve products whose stock is at or below threshold, ordered by stock ascending."""
    stmt = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.stock_quantity <= threshold)
        .order_by(Product.stock_quantity.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_products_by_category_count(db: AsyncSession) -> list[tuple[str, int]]:
    """Return product counts grouped by category name for charts.

    Returns:
        list[tuple[str, int]]: e.g. [("Electronics", 24), ("Clothing", 15), ("Uncategorized", 3)]
    """
    stmt = (
        select(
            func.coalesce(Category.name, "Uncategorized").label("category_name"),
            func.count(Product.id).label("product_count"),
        )
        .select_from(Product)
        .outerjoin(Category, Product.category_id == Category.id)
        .group_by(Category.name)
        .order_by(func.count(Product.id).desc())
    )
    result = await db.execute(stmt)
    return [(row[0], int(row[1])) for row in result.all()]


async def get_monthly_product_counts(
    db: AsyncSession, months: int = 6
) -> list[tuple[str, int]]:
    """Return product counts grouped by month (YYYY-MM) for the last N months.

    Returns:
        list[tuple[str, int]]: e.g. [("2026-05", 10), ("2026-06", 14), ...]
    """
    now = datetime.now(timezone.utc)
    # Generate ordered month keys for the last `months`
    month_keys: list[str] = []
    for i in range(months - 1, -1, -1):
        # calculate approximate year and month
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_keys.append(f"{year:04d}-{month:02d}")

    # Query products created in the past range
    start_year = int(month_keys[0].split("-")[0])
    start_month = int(month_keys[0].split("-")[1])
    start_date = datetime(start_year, start_month, 1)

    month_str_expr = func.date_format(Product.created_at, "%Y-%m")

    stmt = (
        select(
            month_str_expr.label("month_str"),
            func.count(Product.id).label("count"),
        )
        .where(Product.created_at >= start_date)
        .group_by(month_str_expr)
    )

    try:
        result = await db.execute(stmt)
        data_map = {row[0]: int(row[1]) for row in result.all() if row[0] is not None}
    except Exception:
        # Fallback for databases like SQLite that don't support DATE_FORMAT
        fallback_stmt = select(Product.created_at).where(Product.created_at >= start_date)
        result = await db.execute(fallback_stmt)
        data_map = {}
        for row in result.all():
            dt = row[0]
            if dt:
                m_str = dt.strftime("%Y-%m")
                data_map[m_str] = data_map.get(m_str, 0) + 1

    return [(k, data_map.get(k, 0)) for k in month_keys]
