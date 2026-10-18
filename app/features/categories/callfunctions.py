"""Call functions for categories orchestrating repository and business logic."""

from __future__ import annotations

import math
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.features.categories import logic, repository
from app.features.categories.models import Category
from app.features.categories.schemas import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
    PaginationMeta,
)
from app.logging_config import get_logger

logger = get_logger(__name__)


async def list_categories_call(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> CategoryListResponse:
    """Fetch paginated categories with product counts and pagination metadata."""
    categories_with_count, total = await repository.get_categories(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            product_count=prod_count,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        for cat, prod_count in categories_with_count
    ]

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return CategoryListResponse(
        categories=items,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


async def get_all_categories_call(db: AsyncSession) -> list[CategoryResponse]:
    """Fetch all categories for dropdown selection."""
    categories = await repository.get_all_categories(db)
    return [
        CategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            product_count=0,
            created_at=cat.created_at,
            updated_at=cat.updated_at,
        )
        for cat in categories
    ]


async def get_category_call(db: AsyncSession, category_id: int) -> CategoryResponse:
    """Fetch a single category by ID with its product count."""
    category = await repository.get_category_by_id(db, category_id)
    if not category:
        raise NotFoundError(f"Category with ID {category_id} not found")

    product_count = len(category.products) if category.products else 0
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        product_count=product_count,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


async def create_category_call(
    db: AsyncSession, schema: CategoryCreate
) -> CategoryResponse:
    """Validate and create a new category."""
    existing = await repository.get_category_by_name(db, schema.name)
    logic.validate_category_create(existing)

    category = await repository.create_category(
        db,
        data={"name": schema.name.strip(), "description": schema.description},
    )
    logger.info("Category created successfully: id=%d name=%s", category.id, category.name)

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        product_count=0,
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


async def update_category_call(
    db: AsyncSession, category_id: int, schema: CategoryUpdate
) -> CategoryResponse:
    """Validate and update an existing category."""
    category = await repository.get_category_by_id(db, category_id)
    if not category:
        raise NotFoundError(f"Category with ID {category_id} not found")

    update_data = schema.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        new_name = update_data["name"].strip()
        if new_name.lower() != category.name.lower():
            existing = await repository.get_category_by_name(db, new_name)
            logic.validate_category_create(existing)
        update_data["name"] = new_name

    updated_cat = await repository.update_category(db, category, update_data)
    logger.info("Category updated successfully: id=%d", updated_cat.id)

    product_count = len(updated_cat.products) if updated_cat.products else 0
    return CategoryResponse(
        id=updated_cat.id,
        name=updated_cat.name,
        description=updated_cat.description,
        product_count=product_count,
        created_at=updated_cat.created_at,
        updated_at=updated_cat.updated_at,
    )


async def delete_category_call(db: AsyncSession, category_id: int) -> None:
    """Validate and delete a category."""
    category = await repository.get_category_by_id(db, category_id)
    if not category:
        raise NotFoundError(f"Category with ID {category_id} not found")

    product_count = len(category.products) if category.products else 0
    logic.validate_category_delete(category, product_count=product_count)

    await repository.delete_category(db, category)
    logger.info("Category deleted successfully: id=%d name=%s", category.id, category.name)
