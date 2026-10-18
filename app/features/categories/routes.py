"""Category routes — both HTML template endpoints and JSON API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.dependencies import get_current_user, require_role, validate_csrf
from app.core.permissions import Role
from app.core.security import generate_csrf_token
from app.database import get_db
from app.features.categories.callfunctions import (
    create_category_call,
    delete_category_call,
    get_all_categories_call,
    get_category_call,
    list_categories_call,
    update_category_call,
)
from app.features.categories.schemas import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.features.users.models import User

settings = get_settings()

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _ctx(request: Request, current_user: User, **kwargs) -> dict:
    csrf = generate_csrf_token()
    return {"request": request, "current_user": current_user, "csrf_token": csrf, **kwargs}


categories_router = APIRouter()


# ===========================================================================
# HTML Routes (Authenticated browser views)
# ===========================================================================


@categories_router.get(
    "/categories",
    response_class=HTMLResponse,
    summary="List categories HTML view",
)
async def categories_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(settings.ITEMS_PER_PAGE, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Render category listing page."""
    data = await list_categories_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return templates.TemplateResponse(
        request=request,
        name="categories/list.html",
        context=_ctx(
            request,
            current_user,
            categories=data.categories,
            pagination=data.pagination,
            search=search or "",
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@categories_router.get(
    "/categories/create",
    response_class=HTMLResponse,
    summary="Create category form HTML view",
)
async def category_create_view(
    request: Request,
    current_user: User = Depends(require_role(Role.MANAGER)),
):
    """Render create category form."""
    return templates.TemplateResponse(
        request=request,
        name="categories/create.html",
        context=_ctx(request, current_user),
    )


@categories_router.post(
    "/categories/create",
    dependencies=[Depends(validate_csrf)],
    summary="Process create category form",
)
async def category_create_submit(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Handle category creation form submit."""
    schema = CategoryCreate(name=name, description=description)
    await create_category_call(db=db, schema=schema)
    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)


@categories_router.get(
    "/categories/{category_id}/edit",
    response_class=HTMLResponse,
    summary="Edit category form HTML view",
)
async def category_edit_view(
    request: Request,
    category_id: int,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Render edit category form."""
    category = await get_category_call(db=db, category_id=category_id)
    return templates.TemplateResponse(
        request=request,
        name="categories/edit.html",
        context=_ctx(request, current_user, category=category),
    )


@categories_router.post(
    "/categories/{category_id}/edit",
    dependencies=[Depends(validate_csrf)],
    summary="Process edit category form",
)
async def category_edit_submit(
    request: Request,
    category_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Handle category update form submit."""
    schema = CategoryUpdate(name=name, description=description)
    await update_category_call(db=db, category_id=category_id, schema=schema)
    return RedirectResponse(url="/categories", status_code=status.HTTP_303_SEE_OTHER)


# ===========================================================================
# API Routes (JSON Endpoints)
# ===========================================================================


@categories_router.get(
    "/api/categories/all",
    response_model=list[CategoryResponse],
    summary="Get all categories without pagination",
)
async def api_get_all_categories(
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Return all categories for select menus and dropdowns."""
    return await get_all_categories_call(db=db)


@categories_router.get(
    "/api/categories",
    response_model=CategoryListResponse,
    summary="List categories paginated",
)
async def api_list_categories(
    page: int = Query(1, ge=1),
    per_page: int = Query(settings.ITEMS_PER_PAGE, ge=1, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of categories with product counts."""
    return await list_categories_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@categories_router.post(
    "/api/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(validate_csrf)],
    summary="Create category",
)
async def api_create_category(
    payload: CategoryCreate,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    return await create_category_call(db=db, schema=payload)


@categories_router.get(
    "/api/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Get category details",
)
async def api_get_category(
    category_id: int,
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Fetch details for a single category."""
    return await get_category_call(db=db, category_id=category_id)


@categories_router.put(
    "/api/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(validate_csrf)],
    summary="Update category",
)
async def api_update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing category."""
    return await update_category_call(db=db, category_id=category_id, schema=payload)


@categories_router.delete(
    "/api/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_csrf)],
    summary="Delete category",
)
async def api_delete_category(
    category_id: int,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (Admin only)."""
    await delete_category_call(db=db, category_id=category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
