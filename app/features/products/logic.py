"""Business logic and validation rules for products."""

from __future__ import annotations

from typing import Any, Optional

from app.exceptions import DuplicateError
from app.features.products.models import Product


def validate_product_create(existing_by_sku: Product | None) -> None:
    """Validate product creation constraints.

    Raises:
        DuplicateError: If a product with the same SKU already exists.
    """
    if existing_by_sku is not None:
        raise DuplicateError(f"Product with SKU '{existing_by_sku.sku}' already exists")


def validate_product_update(
    product: Product,
    update_data: dict[str, Any],
    existing_by_sku: Optional[Product] = None,
) -> None:
    """Validate product update constraints.

    Raises:
        DuplicateError: If SKU is being changed to an existing one belonging to another product.
    """
    new_sku = update_data.get("sku")
    if new_sku and new_sku.strip().upper() != product.sku.upper():
        if existing_by_sku is not None and existing_by_sku.id != product.id:
            raise DuplicateError(f"Product with SKU '{new_sku}' already exists")


def check_low_stock(product: Product, threshold: int) -> bool:
    """Return True if the product's stock is at or below the low stock threshold."""
    return product.stock_quantity <= threshold
