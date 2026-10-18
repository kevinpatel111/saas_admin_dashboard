"""Dashboard routes — main administration view and stats/chart API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.core.permissions import Role
from app.core.security import generate_csrf_token
from app.database import get_db
from app.features.dashboard.callfunctions import (
    get_chart_data_call,
    get_dashboard_stats_call,
    get_dashboard_summary_call,
)
from app.features.users.models import User

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _ctx(request: Request, current_user: User, **kwargs) -> dict:
    csrf = generate_csrf_token()
    return {"request": request, "current_user": current_user, "csrf_token": csrf, **kwargs}


dashboard_router = APIRouter()


@dashboard_router.get("/", summary="Root redirect to dashboard")
async def root_redirect():
    """Redirect root path to the dashboard."""
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)


@dashboard_router.get(
    "/dashboard",
    response_class=HTMLResponse,
    summary="Dashboard HTML view",
)
async def dashboard_view(
    request: Request,
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Render dashboard page with stats, charts, recent activity, and low-stock alerts."""
    summary = await get_dashboard_summary_call(db=db)
    return templates.TemplateResponse(
        request=request,
        name="dashboard/index.html",
        context=_ctx(
            request,
            current_user,
            stats=summary["stats"],
            charts=summary["charts"],
            recent_users=summary["recent_users"],
            recent_products=summary["recent_products"],
            low_stock_products=summary["low_stock_products"],
        ),
    )


@dashboard_router.get(
    "/api/dashboard/stats",
    response_model=dict[str, int],
    summary="Get dashboard statistics",
)
async def api_dashboard_stats(
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Return JSON aggregated statistics."""
    return await get_dashboard_stats_call(db=db)


@dashboard_router.get(
    "/api/dashboard/charts",
    summary="Get dashboard chart data",
)
async def api_dashboard_charts(
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return JSON monthly activity and category distribution formatted for Chart.js."""
    return await get_chart_data_call(db=db)
