"""User repository — database queries for user management."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User


async def get_users(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
) -> tuple[list[User], int]:
    """Fetch paginated, filtered, and sorted users with total count.

    Returns:
        tuple[list[User], int]: (users_list, total_count)
    """
    stmt = select(User)

    # 1. Search filter: name OR email (case-insensitive)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(term),
                func.lower(User.email).like(term),
            )
        )

    # 2. Role filter
    if role_filter and role_filter.strip():
        stmt = stmt.where(User.role == role_filter.strip().lower())

    # 3. Status filter
    if status_filter is not None:
        stmt = stmt.where(User.is_active == status_filter)

    # Count query before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total_count = total_result.scalar() or 0

    # 4. Sorting
    valid_sort_columns = {
        "id": User.id,
        "name": User.name,
        "email": User.email,
        "role": User.role,
        "is_active": User.is_active,
        "created_at": User.created_at,
        "updated_at": User.updated_at,
    }
    sort_column = valid_sort_columns.get(sort_by.lower(), User.id)

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
    users = list(result.scalars().all())

    return users, total_count


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Fetch user by primary key ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch user by normalized email address."""
    result = await db.execute(
        select(User).where(User.email == email.strip().lower())
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: dict) -> User:
    """Insert a new user record and refresh attributes."""
    user = User(**user_data)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, update_data: dict) -> User:
    """Update user attributes from dictionary and refresh."""
    for key, value in update_data.items():
        setattr(user, key, value)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    """Delete a user entity from the database."""
    await db.delete(user)
    await db.flush()


async def count_active_admins(db: AsyncSession) -> int:
    """Count users with admin role and is_active=True."""
    stmt = select(func.count()).select_from(User).where(
        User.role == "admin",
        User.is_active.is_(True),
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def count_users(db: AsyncSession, active_only: bool = False) -> int:
    """Count total users, optionally filtered to active only."""
    stmt = select(func.count()).select_from(User)
    if active_only:
        stmt = stmt.where(User.is_active.is_(True))
    result = await db.execute(stmt)
    return result.scalar() or 0
