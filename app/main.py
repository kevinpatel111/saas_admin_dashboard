"""SaaS Admin Dashboard - Main FastAPI Application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.exceptions import AppException
from app.features.auth.routes import auth_router
from app.features.categories.routes import categories_router
from app.features.dashboard.routes import dashboard_router
from app.features.products.routes import products_router
from app.features.reports.routes import reports_router
from app.features.users.routes import users_router
from app.logging_config import get_logger, setup_logging

settings = get_settings()
logger = get_logger(__name__)

_BASE_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _BASE_DIR / "static"
_TEMPLATES_DIR = _BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown routines."""
    setup_logging(debug=settings.DEBUG)
    logger.info("Starting up %s (Debug: %s)", settings.APP_NAME, settings.DEBUG)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Static Files
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# Global Health Check API Endpoint
@app.get("/api/health", tags=["Health"], summary="Service health status")
async def health_check():
    """Health check endpoint for Docker container checks and uptime monitoring."""
    return {"status": "ok", "app": settings.APP_NAME}


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle custom application exceptions for both API and browser requests."""
    is_api = request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")
    if is_api:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request,
            name="errors/404.html",
            context={"request": request},
            status_code=404,
        )
    if exc.status_code == 403:
        return templates.TemplateResponse(
            request=request,
            name="errors/403.html",
            context={"request": request, "current_user": getattr(request.state, "user", None)},
            status_code=403,
        )

    return templates.TemplateResponse(
        request=request,
        name="errors/500.html",
        context={"request": request, "error": exc.detail},
        status_code=exc.status_code,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette and FastAPI HTTPExceptions."""
    # Allow explicit redirects (e.g., from auth dependencies with Location header)
    if exc.status_code in (301, 302, 303, 307, 308) and exc.headers and "Location" in exc.headers:
        return RedirectResponse(
            url=exc.headers["Location"],
            status_code=exc.status_code,
        )

    is_api = request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", "")
    if is_api:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request,
            name="errors/404.html",
            context={"request": request},
            status_code=404,
        )
    if exc.status_code == 403:
        return templates.TemplateResponse(
            request=request,
            name="errors/403.html",
            context={"request": request, "current_user": getattr(request.state, "user", None)},
            status_code=403,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


# ---------------------------------------------------------------------------
# Routers Registration
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(reports_router)
