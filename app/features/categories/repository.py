"""Category repository — database queries for category management."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.categories.models import Category
from app.features.products.models import Product


async def get_categories(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> tuple[list[tuple[Category, int]], int]:
    """Fetch paginated, filtered, and sorted categories along with product count and total count.

    Returns:
        tuple[list[tuple[Category, int]], int]: A tuple of ((category, product_count) list, total_count).
    """
    # Base query joining Category with Product count
    stmt = (
        select(Category, func.count(Product.id).label("product_count"))
        .outerjoin(Product, Category.id == Product.category_id)
        .group_by(Category.id)
    )

    # Search filter by name or description
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Category.name).like(term),
                func.lower(Category.description).like(term),
            )
        )

    # Count query for total matching categories
    count_subquery = (
        select(Category.id)
    )
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        count_subquery = count_subquery.where(
            or_(
                func.lower(Category.name).like(term),
                func.lower(Category.description).like(term),
            )
        )
    count_stmt = select(func.count()).select_from(count_subquery.subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0

    # Sorting
    valid_sort_columns = {
        "id": Category.id,
        "name": Category.name,
        "created_at": Category.created_at,
        "updated_at": Category.updated_at,
        "product_count": func.count(Product.id),
    }
    sort_column = valid_sort_columns.get(sort_by.lower(), Category.id)

    if sort_order.lower() == "desc":
        stmt = stmt.order_by(sort_column.desc())
    else:
        stmt = stmt.order_by(sort_column.asc())

    # Pagination
    safe_page = max(1, page)
    safe_per_page = max(1, per_page)
    offset = (safe_page - 1) * safe_per_page
    stmt = stmt.offset(offset).limit(safe_per_page)

    result = await db.execute(stmt)
    rows = result.all()

    # rows is list of Row(Category, product_count)
    categories_with_count = [(row[0], row[1]) for row in rows]
    return categories_with_count, total_count


async def get_all_categories(db: AsyncSession) -> list[Category]:
    """Fetch all categories without pagination (for dropdowns), ordered by name."""
    stmt = select(Category).order_by(Category.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    """Fetch category by primary key ID."""
    stmt = select(Category).where(Category.id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_category_by_name(db: AsyncSession, name: str) -> Category | None:
    """Fetch category by exact name (case-insensitive check)."""
    stmt = select(Category).where(func.lower(Category.name) == name.strip().lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, data: dict) -> Category:
    """Insert a new category and refresh."""
    category = Category(**data)
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, category: Category, data: dict) -> Category:
    """Update category attributes and refresh."""
    for key, value in data.items():
        setattr(category, key, value)
    await db.flush()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category: Category) -> None:
    """Delete a category entity."""
    await db.delete(category)
    await db.flush()


async def count_categories(db: AsyncSession) -> int:
    """Count total categories."""
    stmt = select(func.count()).select_from(Category)
    result = await db.execute(stmt)
    return result.scalar() or 0
