"""Pure business logic and validation rules for user management."""

from __future__ import annotations

from typing import Any

from app.core.security import hash_password
from app.exceptions import DuplicateError, ForbiddenError, ValidationError
from app.features.users.models import User
from app.features.users.schemas import UserCreate, UserUpdate


def validate_user_create(existing_user: User | None) -> None:
    """Validate that email is not already registered.

    Raises DuplicateError if user with email already exists.
    """
    if existing_user is not None:
        raise DuplicateError("A user with this email already exists.")


def prepare_user_data(data: UserCreate) -> dict[str, Any]:
    """Convert UserCreate schema into database attributes with hashed password."""
    return {
        "name": data.name.strip(),
        "email": data.email.strip().lower(),
        "password_hash": hash_password(data.password),
        "role": data.role.strip().lower(),
        "is_active": data.is_active,
    }


def validate_user_update(
    user: User,
    data: UserUpdate,
    current_user: User,
    active_admin_count: int,
) -> dict[str, Any]:
    """Validate user update permissions and business rules.

    Rules enforced:
    - Non-admins cannot modify roles (prevent self or peer role escalation).
    - Cannot deactivate or demote the last remaining active admin.
    - Password is hashed if provided.
    - Returns cleaned dictionary of changed fields only.
    """
    update_dict: dict[str, Any] = {}

    # Check name change
    if data.name is not None and data.name.strip() != user.name:
        update_dict["name"] = data.name.strip()

    # Check email change
    if data.email is not None and data.email.strip().lower() != user.email:
        update_dict["email"] = data.email.strip().lower()

    # Check password change
    if data.password is not None and len(data.password.strip()) > 0:
        update_dict["password_hash"] = hash_password(data.password)

    # Check role change
    if data.role is not None and data.role != user.role:
        # Only admin users are allowed to change roles
        if current_user.role != "admin":
            raise ForbiddenError("Only administrators can modify user roles.")

        # If demoting an active admin, ensure there is at least one other active admin
        if user.role == "admin" and user.is_active and data.role != "admin":
            if active_admin_count <= 1:
                raise ValidationError("Cannot demote the last remaining active administrator.")

        update_dict["role"] = data.role

    # Check active status change
    if data.is_active is not None and data.is_active != user.is_active:
        # Only admin or manager can change status, but deactivating last active admin is prohibited
        if user.role == "admin" and user.is_active and not data.is_active:
            if active_admin_count <= 1:
                raise ValidationError("Cannot deactivate the last remaining active administrator.")

        # Non-admins cannot deactivate administrators
        if user.role == "admin" and current_user.role != "admin":
            raise ForbiddenError("Only administrators can modify administrator status.")

        update_dict["is_active"] = data.is_active

    return update_dict
