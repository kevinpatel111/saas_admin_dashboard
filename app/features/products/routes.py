"""Product routes — both HTML template endpoints and JSON API endpoints."""

from __future__ import annotations

from decimal import Decimal
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
from app.features.categories.callfunctions import get_all_categories_call
from app.features.products.callfunctions import (
    create_product_call,
    delete_product_call,
    get_low_stock_products_call,
    get_product_call,
    list_products_call,
    update_product_call,
)
from app.features.products.schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.features.users.models import User

settings = get_settings()

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


def _ctx(request: Request, current_user: User, **kwargs) -> dict:
    csrf = generate_csrf_token()
    return {"request": request, "current_user": current_user, "csrf_token": csrf, **kwargs}


products_router = APIRouter()


# ===========================================================================
# HTML Routes (Authenticated browser views)
# ===========================================================================


@products_router.get(
    "/products",
    response_class=HTMLResponse,
    summary="List products HTML view",
)
async def products_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(settings.ITEMS_PER_PAGE, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Render products listing page with search and filters."""
    data = await list_products_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    categories = await get_all_categories_call(db=db)

    return templates.TemplateResponse(
        request=request,
        name="products/list.html",
        context=_ctx(
            request,
            current_user,
            products=data.products,
            pagination=data.pagination,
            categories=categories,
            search=search or "",
            category_id=category_id,
            status=status_filter or "",
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@products_router.get(
    "/products/create",
    response_class=HTMLResponse,
    summary="Create product form HTML view",
)
async def product_create_view(
    request: Request,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Render create product form with category dropdown."""
    categories = await get_all_categories_call(db=db)
    return templates.TemplateResponse(
        request=request,
        name="products/create.html",
        context=_ctx(request, current_user, categories=categories),
    )


@products_router.post(
    "/products/create",
    dependencies=[Depends(validate_csrf)],
    summary="Process create product form",
)
async def product_create_submit(
    request: Request,
    name: str = Form(...),
    sku: str = Form(...),
    description: Optional[str] = Form(None),
    price: Decimal = Form(...),
    stock_quantity: int = Form(...),
    category_id: Optional[int] = Form(None),
    status: str = Form("active"),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Handle product creation form submit."""
    schema = ProductCreate(
        name=name,
        sku=sku,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        category_id=category_id,
        status=status,
    )
    await create_product_call(db=db, schema=schema)
    return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


@products_router.get(
    "/products/{product_id}/edit",
    response_class=HTMLResponse,
    summary="Edit product form HTML view",
)
async def product_edit_view(
    request: Request,
    product_id: int,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Render edit product form."""
    product = await get_product_call(db=db, product_id=product_id)
    categories = await get_all_categories_call(db=db)
    return templates.TemplateResponse(
        request=request,
        name="products/edit.html",
        context=_ctx(request, current_user, product=product, categories=categories),
    )


@products_router.post(
    "/products/{product_id}/edit",
    dependencies=[Depends(validate_csrf)],
    summary="Process edit product form",
)
async def product_edit_submit(
    request: Request,
    product_id: int,
    name: Optional[str] = Form(None),
    sku: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    price: Optional[Decimal] = Form(None),
    stock_quantity: Optional[int] = Form(None),
    category_id: Optional[int] = Form(None),
    status: Optional[str] = Form(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Handle product update form submit."""
    schema = ProductUpdate(
        name=name,
        sku=sku,
        description=description,
        price=price,
        stock_quantity=stock_quantity,
        category_id=category_id,
        status=status,
    )
    await update_product_call(db=db, product_id=product_id, schema=schema)
    return RedirectResponse(url="/products", status_code=status.HTTP_303_SEE_OTHER)


# ===========================================================================
# API Routes (JSON Endpoints)
# ===========================================================================


@products_router.get(
    "/api/products",
    response_model=ProductListResponse,
    summary="List products paginated",
)
async def api_list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(settings.ITEMS_PER_PAGE, ge=1, le=100),
    search: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated list of products."""
    return await list_products_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@products_router.post(
    "/api/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(validate_csrf)],
    summary="Create product",
)
async def api_create_product(
    payload: ProductCreate,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product."""
    return await create_product_call(db=db, schema=payload)


@products_router.get(
    "/api/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
)
async def api_get_product(
    product_id: int,
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Fetch details for a single product."""
    return await get_product_call(db=db, product_id=product_id)


@products_router.put(
    "/api/products/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(validate_csrf)],
    summary="Update product",
)
async def api_update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product."""
    return await update_product_call(db=db, product_id=product_id, schema=payload)


@products_router.delete(
    "/api/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(validate_csrf)],
    summary="Delete product",
)
async def api_delete_product(
    product_id: int,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a product (Admin only)."""
    await delete_product_call(db=db, product_id=product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
