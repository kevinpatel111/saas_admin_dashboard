"""User management HTTP and API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role, validate_csrf
from app.core.permissions import Role
from app.core.security import generate_csrf_token
from app.database import get_db
from app.exceptions import AppException
from app.features.users.callfunctions import (
    create_user_call,
    delete_user_call,
    get_user_call,
    list_users_call,
    update_user_call,
)
from app.features.users.models import User
from app.features.users.schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.logging_config import get_logger

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

users_router = APIRouter(tags=["Users"])


def _ctx(request: Request, current_user: User, **kwargs) -> dict:
    """Helper to generate template context with fresh CSRF token."""
    csrf = generate_csrf_token()
    return {"request": request, "current_user": current_user, "csrf_token": csrf, **kwargs}


# ---------------------------------------------------------------------------
# HTML Browser Routes
# ---------------------------------------------------------------------------

@users_router.get("/users", response_class=HTMLResponse)
async def users_list_page(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """Render users list table page with filtering, searching, and pagination."""
    status_bool: Optional[bool] = None
    if status_filter is not None and status_filter != "":
        if status_filter.lower() in ("true", "1", "active"):
            status_bool = True
        elif status_filter.lower() in ("false", "0", "inactive"):
            status_bool = False

    data = await list_users_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        role_filter=role,
        status_filter=status_bool,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return templates.TemplateResponse(
        request=request,
        name="users/list.html",
        context=_ctx(
            request,
            current_user,
            users=data["users"],
            pagination=data["pagination"],
            search=search or "",
            role_filter=role or "",
            status_filter=status_filter or "",
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@users_router.get("/users/create", response_class=HTMLResponse)
async def user_create_page(
    request: Request,
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Render user creation form."""
    return templates.TemplateResponse(
        request=request,
        name="users/create.html",
        context=_ctx(request, current_user, form_data={}, error=None),
    )


@users_router.post("/users/create")
async def user_create_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("staff"),
    is_active: bool = Form(True),
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(validate_csrf),
):
    """Handle user creation form POST submission."""
    form_data = {
        "name": name,
        "email": email,
        "role": role,
        "is_active": is_active,
    }
    try:
        user_in = UserCreate(
            name=name,
            email=email,
            password=password,
            role=role,
            is_active=is_active,
        )
        await create_user_call(db=db, data=user_in)
        return RedirectResponse(url="/users", status_code=status.HTTP_303_SEE_OTHER)
    except (AppException, PydanticValidationError) as exc:
        error_msg = exc.detail if isinstance(exc, AppException) else str(exc)
        return templates.TemplateResponse(
            request=request,
            name="users/create.html",
            context=_ctx(request, current_user, form_data=form_data, error=error_msg),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


@users_router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def user_edit_page(
    request: Request,
    user_id: int,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Render user edit form."""
    target_user = await get_user_call(db, user_id=user_id)
    return templates.TemplateResponse(
        request=request,
        name="users/edit.html",
        context=_ctx(request, current_user, user=target_user, error=None),
    )


@users_router.post("/users/{user_id}/edit")
async def user_edit_submit(
    request: Request,
    user_id: int,
    name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    role: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(validate_csrf),
):
    """Handle user update form POST submission."""
    try:
        target_user = await get_user_call(db, user_id=user_id)
        user_update = UserUpdate(
            name=name if name else None,
            email=email if email else None,
            password=password if password else None,
            role=role if role else None,
            is_active=is_active if is_active is not None else None,
        )
        await update_user_call(db=db, user_id=user_id, data=user_update, current_user=current_user)
        return RedirectResponse(url="/users", status_code=status.HTTP_303_SEE_OTHER)
    except (AppException, PydanticValidationError) as exc:
        error_msg = exc.detail if isinstance(exc, AppException) else str(exc)
        target_user = await get_user_call(db, user_id=user_id)
        return templates.TemplateResponse(
            request=request,
            name="users/edit.html",
            context=_ctx(request, current_user, user=target_user, error=error_msg),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@users_router.get("/api/users", response_model=UserListResponse)
async def api_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    status_filter: Optional[bool] = Query(None, alias="status"),
    sort_by: str = Query("id"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """API: Get paginated user list with filtering and search."""
    data = await list_users_call(
        db=db,
        page=page,
        per_page=per_page,
        search=search,
        role_filter=role,
        status_filter=status_filter,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in data["users"]],
        pagination=data["pagination"],
    )


@users_router.post("/api/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def api_create_user(
    payload: UserCreate,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """API: Create a new user (admin only)."""
    user = await create_user_call(db=db, data=payload)
    return UserResponse.model_validate(user)


@users_router.get("/api/users/{user_id}", response_model=UserResponse)
async def api_get_user(
    user_id: int,
    current_user: User = Depends(require_role(Role.STAFF)),
    db: AsyncSession = Depends(get_db),
):
    """API: Get single user details by ID."""
    user = await get_user_call(db=db, user_id=user_id)
    return UserResponse.model_validate(user)


@users_router.put("/api/users/{user_id}", response_model=UserResponse)
async def api_update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_role(Role.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """API: Update an existing user by ID (manager+)."""
    updated_user = await update_user_call(
        db=db, user_id=user_id, data=payload, current_user=current_user
    )
    return UserResponse.model_validate(updated_user)


@users_router.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_user(
    user_id: int,
    current_user: User = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """API: Delete an existing user by ID (admin only)."""
    await delete_user_call(db=db, user_id=user_id, current_user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
