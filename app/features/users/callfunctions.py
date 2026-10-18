"""User management use-case orchestration / call functions."""

from __future__ import annotations

import math
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.features.users.logic import (
    prepare_user_data,
    validate_user_create,
    validate_user_update,
)
from app.features.users.models import User
from app.features.users.repository import (
    count_active_admins,
    create_user,
    delete_user,
    get_user_by_email,
    get_user_by_id,
    get_users,
    update_user,
)
from app.features.users.schemas import UserCreate, UserUpdate
from app.logging_config import get_logger

logger = get_logger(__name__)


async def list_users_call(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> dict[str, Any]:
    """Orchestrate paginated user listing with meta information."""
    users, total = await get_users(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        role_filter=role_filter,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return {
        "users": users,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        },
    }


async def get_user_call(db: AsyncSession, user_id: int) -> User:
    """Fetch user by ID or raise NotFoundError."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found.")
    return user


async def create_user_call(db: AsyncSession, data: UserCreate) -> User:
    """Orchestrate user creation: check duplicates, prepare hash, and persist."""
    existing_user = await get_user_by_email(db, data.email)
    validate_user_create(existing_user)

    user_dict = prepare_user_data(data)
    user = await create_user(db, user_dict)
    logger.info("Created new user: ID=%s, email=%s, role=%s", user.id, user.email, user.role)
    return user


async def update_user_call(
    db: AsyncSession,
    user_id: int,
    data: UserUpdate,
    current_user: User,
) -> User:
    """Orchestrate user update: validate role & admin rules, check email collision, and update."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found.")

    # If updating email, ensure it's not taken by another user
    if data.email is not None and data.email.strip().lower() != user.email:
        other_user = await get_user_by_email(db, data.email)
        if other_user and other_user.id != user.id:
            from app.exceptions import DuplicateError
            raise DuplicateError("A user with this email already exists.")

    active_admins = await count_active_admins(db)
    update_data = validate_user_update(
        user=user,
        data=data,
        current_user=current_user,
        active_admin_count=active_admins,
    )

    if not update_data:
        return user

    updated = await update_user(db, user, update_data)
    logger.info("Updated user: ID=%s, fields=%s", updated.id, list(update_data.keys()))
    return updated


async def delete_user_call(
    db: AsyncSession,
    user_id: int,
    current_user: User,
) -> None:
    """Orchestrate user deletion: prevent self-deletion and deleting last active admin."""
    if current_user.id == user_id:
        raise ValidationError("You cannot delete your own account.")

    user = await get_user_by_id(db, user_id)
    if not user:
        raise NotFoundError(f"User with ID {user_id} not found.")

    # Prevent deleting admin if it's the last active admin
    if user.role == "admin" and user.is_active:
        active_admins = await count_active_admins(db)
        if active_admins <= 1:
            raise ValidationError("Cannot delete the last remaining active administrator.")

    await delete_user(db, user)
    logger.info("Deleted user: ID=%s, email=%s", user.id, user.email)
