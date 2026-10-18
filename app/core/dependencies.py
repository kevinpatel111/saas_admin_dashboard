"""FastAPI dependencies for authentication, authorisation, and CSRF."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role, has_minimum_role
from app.core.security import decode_access_token, verify_csrf_token
from app.database import get_db

if TYPE_CHECKING:
    from app.features.users.models import User

# Optional bearer — allows both cookie and header auth
_optional_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> User:
    """Extract JWT from cookie or ``Authorization`` header, return the user.

    * Browser requests without a valid token are redirected to ``/login``.
    * API requests receive a ``401`` JSON response.
    """
    # 1. Resolve the token
    token: str | None = None
    if bearer:
        token = bearer.credentials
    else:
        token = request.cookies.get("access_token")

    is_api = request.url.path.startswith("/api/")

    if not token:
        if is_api:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    # 2. Decode the token
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        if is_api:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
            )
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    # 3. Load the user from the database (lazy import avoids circular deps)
    from app.features.users.repository import get_user_by_id

    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        if is_api:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    return user


def require_role(minimum_role: Role):
    """Dependency factory: reject users below *minimum_role*."""

    async def _checker(
        current_user: User = Depends(get_current_user),  # type: ignore[assignment]
    ) -> User:
        if not has_minimum_role(current_user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


async def validate_csrf(request: Request) -> None:
    """Validate the CSRF token on state-changing requests.

    Skipped for:
    * Safe HTTP methods (GET, HEAD, OPTIONS).
    * Requests authenticated via ``Authorization: Bearer`` header (API clients).
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Bearer-authenticated API requests don't need CSRF
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return

    csrf_cookie = request.cookies.get("csrf_token")

    # Accept the token from the X-CSRF-Token header (fetch) …
    submitted = request.headers.get("x-csrf-token")

    # … or from a hidden form field.
    if not submitted:
        content_type = request.headers.get("content-type", "")
        if "form" in content_type:
            form = await request.form()
            submitted = form.get("csrf_token")

    if not submitted or not csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing"
        )

    if not verify_csrf_token(submitted) or submitted != csrf_cookie:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF verification failed",
        )
