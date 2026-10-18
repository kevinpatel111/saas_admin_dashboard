"""Business logic and validation rules for categories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.exceptions import DuplicateError, ValidationError

if TYPE_CHECKING:
    from app.features.categories.models import Category


def validate_category_create(existing: Category | None) -> None:
    """Validate category creation rules.

    Raises:
        DuplicateError: If a category with the same name already exists.
    """
    if existing is not None:
        raise DuplicateError(f"Category with name '{existing.name}' already exists")


def validate_category_delete(category: Category, product_count: int = 0) -> None:
    """Validate category deletion rules.

    Raises:
        ValidationError: If the category still has associated products.
    """
    if product_count > 0 or (hasattr(category, "products") and bool(category.products)):
        raise ValidationError(
            f"Cannot delete category '{category.name}' because it contains associated products"
        )
