"""Authentication repository — database queries for auth operations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a single user by normalized email address."""
    result = await db.execute(
        select(User).where(User.email == email.strip().lower())
    )
    return result.scalar_one_or_none()
