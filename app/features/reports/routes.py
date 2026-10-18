"""Reports routes — report dashboard page and CSV export endpoints."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
from app.core.permissions import Role
from app.core.security import generate_csrf_token
from app.database import get_db
from app.features.categories.callfunctions import get_all_categories_call
from app.features.reports.callfunctions import (
    export_products_csv_call,
    export_users_csv_call,
)
from app.features.users.models import User

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _ctx(request: Request, current_user: User, **kwargs) -> dict:
    csrf = generate_csrf_token()
    return {"request": request, "current_user": current_user, "csrf_token": csrf, **kwargs}


reports_router = APIRouter()


@reports_router.get(
    "/reports",
    response_class=HTMLResponse,
    summary="Reports HTML view",
)
async def reports_view(
    request: Request,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Render reports and exports overview page."""
    categories = await get_all_categories_call(db=db)
    return templates.TemplateResponse(
        request=request,
        name="reports/index.html",
        context=_ctx(request, current_user, categories=categories),
    )


@reports_router.get(
    "/api/reports/export/users",
    summary="Export filtered users as CSV",
)
async def export_users_csv(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a CSV file containing user records."""
    csv_str = await export_users_csv_call(
        db=db,
        search=search,
        role_filter=role,
        status_filter=is_active,
    )

    csv_bytes = io.BytesIO(csv_str.encode("utf-8"))
    headers = {
        "Content-Disposition": 'attachment; filename="users_export.csv"',
    }
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers=headers,
    )


@reports_router.get(
    "/api/reports/export/products",
    summary="Export filtered products as CSV",
)
async def export_products_csv(
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a CSV file containing product records."""
    csv_str = await export_products_csv_call(
        db=db,
        search=search,
        category_id=category_id,
        status_filter=status,
    )

    csv_bytes = io.BytesIO(csv_str.encode("utf-8"))
    headers = {
        "Content-Disposition": 'attachment; filename="products_export.csv"',
    }
    return StreamingResponse(
        csv_bytes,
        media_type="text/csv",
        headers=headers,
    )
