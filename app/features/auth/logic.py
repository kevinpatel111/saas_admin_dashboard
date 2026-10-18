"""Pure business logic and rules for authentication."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.security import verify_password
from app.exceptions import AuthenticationError
from app.features.users.models import User


def authenticate_user(user: User | None, password: str) -> User:
    """Verify password against user hash and confirm active status.

    Raises AuthenticationError on invalid credentials or inactive account.
    """
    if user is None:
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is inactive. Please contact an administrator.")

    return user


def check_rate_limit(
    attempts: list[datetime], max_attempts: int, lockout_minutes: int
) -> None:
    """Check if login attempts exceed the allowed threshold within the lockout window.

    Raises AuthenticationError if rate limit is exceeded.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lockout_minutes)
    recent_attempts = [
        t for t in attempts
        if (t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t) > cutoff
    ]

    if len(recent_attempts) >= max_attempts:
        raise AuthenticationError(
            f"Too many failed login attempts. Please try again after {lockout_minutes} minutes."
        )
