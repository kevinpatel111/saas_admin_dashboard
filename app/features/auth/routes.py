"""Authentication HTTP and API route endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_access_token
from app.database import get_db
from app.exceptions import AppException
from app.features.auth.callfunctions import login_call, logout_call
from app.features.auth.schemas import LoginRequest, TokenResponse
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

auth_router = APIRouter(tags=["Authentication"])


# ---------------------------------------------------------------------------
# HTML Browser Routes
# ---------------------------------------------------------------------------

@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Render login page. Redirect to /dashboard if user already holds a valid token."""
    token = request.cookies.get("access_token")
    if token:
        try:
            decode_access_token(token)
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        except Exception:
            # Token invalid or expired; proceed to show login page
            pass

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request, "error": None},
    )


@auth_router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle HTML login form submission with session cookie creation."""
    try:
        access_token, csrf_token = await login_call(db, email=email, password=password)
    except AppException as exc:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"request": request, "error": exc.detail, "email": email},
            status_code=exc.status_code,
        )
    except Exception as exc:
        logger.exception("Unexpected error during login")
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"request": request, "error": "An unexpected error occurred. Please try again.", "email": email},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    max_age_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    # Set access token cookie (httponly, samesite=lax, configurable secure for HTTPS)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=max_age_seconds,
        path="/",
    )
    # Set csrf token cookie (readable by JS/client, samesite=lax, configurable secure for HTTPS)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=max_age_seconds,
        path="/",
    )
    return response


@auth_router.get("/logout")
async def logout(request: Request):
    """Log out browser session by clearing cookies and redirecting to /login."""
    await logout_call()
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="csrf_token", path="/")
    return response


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@auth_router.post("/api/auth/login", response_model=TokenResponse)
async def api_login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate via API, returning a Bearer access token."""
    access_token, _ = await login_call(db, email=payload.email, password=payload.password)
    return TokenResponse(access_token=access_token, token_type="bearer")
