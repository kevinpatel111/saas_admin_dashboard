"""Call functions for products orchestrating repository and business logic."""

from __future__ import annotations

import math
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import NotFoundError, ValidationError
from app.features.categories.repository import get_category_by_id
from app.features.products import logic, repository
from app.features.products.models import Product
from app.features.products.schemas import (
    PaginationMeta,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _to_product_response(product: Product) -> ProductResponse:
    category_name = product.category.name if product.category else None
    return ProductResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
        description=product.description,
        price=product.price,
        stock_quantity=product.stock_quantity,
        category_id=product.category_id,
        category_name=category_name,
        status=product.status,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def list_products_call(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> ProductListResponse:
    """Fetch paginated products with category information and pagination metadata."""
    products, total = await repository.get_products(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [_to_product_response(prod) for prod in products]
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return ProductListResponse(
        products=items,
        pagination=PaginationMeta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
        ),
    )


async def get_product_call(db: AsyncSession, product_id: int) -> ProductResponse:
    """Fetch a single product by primary key."""
    product = await repository.get_product_by_id(db, product_id)
    if not product:
        raise NotFoundError(f"Product with ID {product_id} not found")
    return _to_product_response(product)


async def create_product_call(
    db: AsyncSession, schema: ProductCreate
) -> ProductResponse:
    """Validate uniqueness and relationships, then create product."""
    # Validate SKU uniqueness
    existing_by_sku = await repository.get_product_by_sku(db, schema.sku)
    logic.validate_product_create(existing_by_sku)

    # Validate category exists if provided
    if schema.category_id is not None:
        category = await get_category_by_id(db, schema.category_id)
        if not category:
            raise ValidationError(f"Category with ID {schema.category_id} does not exist")

    product_data = schema.model_dump()
    product = await repository.create_product(db, product_data)
    logger.info("Product created successfully: id=%d sku=%s", product.id, product.sku)

    return _to_product_response(product)


async def update_product_call(
    db: AsyncSession, product_id: int, schema: ProductUpdate
) -> ProductResponse:
    """Validate updates and modify an existing product."""
    product = await repository.get_product_by_id(db, product_id)
    if not product:
        raise NotFoundError(f"Product with ID {product_id} not found")

    update_data = schema.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] is not None:
        existing_by_sku = await repository.get_product_by_sku(db, update_data["sku"])
        logic.validate_product_update(product, update_data, existing_by_sku)

    if "category_id" in update_data and update_data["category_id"] is not None:
        category = await get_category_by_id(db, update_data["category_id"])
        if not category:
            raise ValidationError(f"Category with ID {update_data['category_id']} does not exist")

    updated_product = await repository.update_product(db, product, update_data)
    logger.info("Product updated successfully: id=%d sku=%s", updated_product.id, updated_product.sku)

    return _to_product_response(updated_product)


async def delete_product_call(db: AsyncSession, product_id: int) -> None:
    """Delete an existing product."""
    product = await repository.get_product_by_id(db, product_id)
    if not product:
        raise NotFoundError(f"Product with ID {product_id} not found")

    await repository.delete_product(db, product)
    logger.info("Product deleted successfully: id=%d sku=%s", product.id, product.sku)


async def get_low_stock_products_call(
    db: AsyncSession, threshold: Optional[int] = None, limit: int = 5
) -> list[ProductResponse]:
    """Retrieve items currently falling below the low stock threshold."""
    thresh = threshold if threshold is not None else settings.LOW_STOCK_THRESHOLD
    items = await repository.get_low_stock_products(db, threshold=thresh, limit=limit)
    return [_to_product_response(p) for p in items]
