"""Role definitions, hierarchy, and permission checks."""

import enum


class Role(str, enum.Enum):
    """Application roles ordered by privilege level."""

    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"


# Numeric privilege level — higher = more privileged.
ROLE_HIERARCHY: dict[Role, int] = {
    Role.ADMIN: 3,
    Role.MANAGER: 2,
    Role.STAFF: 1,
}


def has_minimum_role(user_role: str, required_role: Role) -> bool:
    """Return ``True`` if *user_role* meets or exceeds *required_role*."""
    try:
        user = Role(user_role)
    except ValueError:
        return False
    return ROLE_HIERARCHY.get(user, 0) >= ROLE_HIERARCHY.get(required_role, 0)


def check_permission(user_role: str, feature: str) -> bool:
    """Check whether *user_role* is authorised for *feature*.

    Feature keys follow the pattern ``<resource>.<action>``.
    """
    required = FEATURE_PERMISSIONS.get(feature)
    if required is None:
        return False
    return has_minimum_role(user_role, required)


# Minimum role required for each feature action.
FEATURE_PERMISSIONS: dict[str, Role] = {
    "users.list": Role.STAFF,
    "users.create": Role.ADMIN,
    "users.edit": Role.MANAGER,
    "users.delete": Role.ADMIN,
    "products.list": Role.STAFF,
    "products.create": Role.MANAGER,
    "products.edit": Role.MANAGER,
    "products.delete": Role.ADMIN,
    "categories.list": Role.STAFF,
    "categories.create": Role.MANAGER,
    "categories.edit": Role.MANAGER,
    "categories.delete": Role.ADMIN,
    "reports.export": Role.MANAGER,
    "dashboard.view": Role.STAFF,
}
