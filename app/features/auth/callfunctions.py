"""Authentication use-case orchestration / call functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, generate_csrf_token
from app.exceptions import AuthenticationError
from app.features.auth.logic import authenticate_user, check_rate_limit
from app.features.auth.repository import get_user_by_email
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

# In-memory store for tracking failed login timestamps per email
_login_attempts: dict[str, list[datetime]] = {}


def _cleanup_old_attempts(email_key: str, lockout_minutes: int) -> list[datetime]:
    """Remove expired attempt timestamps for a given email key."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lockout_minutes)
    attempts = _login_attempts.get(email_key, [])
    cleaned = [
        t for t in attempts
        if (t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t) > cutoff
    ]
    if cleaned:
        _login_attempts[email_key] = cleaned
    else:
        _login_attempts.pop(email_key, None)
    return cleaned


async def login_call(
    db: AsyncSession, email: str, password: str
) -> tuple[str, str]:
    """Orchestrate login: check rate limit, verify credentials, and return tokens.

    Returns:
        tuple[str, str]: (access_token, csrf_token)
    """
    normalized_email = email.strip().lower()

    # 1. Check and clean up rate limit records
    recent_attempts = _cleanup_old_attempts(
        normalized_email, settings.LOGIN_LOCKOUT_MINUTES
    )
    check_rate_limit(
        recent_attempts,
        settings.MAX_LOGIN_ATTEMPTS,
        settings.LOGIN_LOCKOUT_MINUTES,
    )

    # 2. Look up user by email
    user = await get_user_by_email(db, normalized_email)

    # 3. Authenticate against password and active state
    try:
        authenticated_user = authenticate_user(user, password)
    except AuthenticationError:
        now = datetime.now(timezone.utc)
        _login_attempts.setdefault(normalized_email, []).append(now)
        logger.warning("Failed login attempt for email: %s", normalized_email)
        raise

    # Clear failed attempts on successful authentication
    _login_attempts.pop(normalized_email, None)

    # 4. Generate JWT and CSRF tokens
    access_token = create_access_token(
        data={"sub": str(authenticated_user.id), "role": authenticated_user.role}
    )
    csrf_token = generate_csrf_token()

    logger.info("User %s (%s) logged in successfully", authenticated_user.id, normalized_email)
    return access_token, csrf_token


async def logout_call() -> None:
    """Orchestrate logout business logic (stateless JWT cleanup)."""
    # Stateless JWT logout; cookies are cleared by the route layer
    return None
