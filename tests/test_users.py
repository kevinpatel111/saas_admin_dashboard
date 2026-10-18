import pytest
from app.features.users.models import User
from app.core.security import hash_password
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_list_users_api(client, admin_user):
    """GET /api/users with admin auth returns user list."""
    response = await client.get("/api/users", headers=auth_headers(admin_user))
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "pagination" in data
    assert any(u["id"] == admin_user.id for u in data["users"])


@pytest.mark.asyncio
async def test_create_user_api(client, admin_user):
    """POST /api/users creates user."""
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123",
        "role": "manager",
        "is_active": True,
    }
    response = await client.post(
        "/api/users", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["email"] == "jane@example.com"
    assert data["role"] == "manager"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client, admin_user):
    """POST /api/users with existing email returns 409."""
    payload = {
        "name": "Another Admin",
        "email": admin_user.email,
        "password": "password12345",
        "role": "staff",
        "is_active": True,
    }
    response = await client.post(
        "/api/users", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_user_api(client, admin_user, staff_user):
    """PUT /api/users/{id} updates user."""
    payload = {
        "name": "Updated Staff Name",
        "role": "manager",
    }
    response = await client.put(
        f"/api/users/{staff_user.id}",
        json=payload,
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Staff Name"
    assert data["role"] == "manager"


@pytest.mark.asyncio
async def test_delete_user_api(client, admin_user, staff_user):
    """DELETE /api/users/{id} deletes user."""
    response = await client.delete(
        f"/api/users/{staff_user.id}",
        headers=auth_headers(admin_user),
    )
    assert response.status_code in (200, 204)

    # Verify deleted user is gone or cannot be retrieved
    get_res = await client.get(
        f"/api/users/{staff_user.id}", headers=auth_headers(admin_user)
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_staff_cannot_create_user(client, staff_user):
    """Staff role gets 403 when attempting to create a user."""
    payload = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "password12345",
        "role": "staff",
    }
    response = await client.post(
        "/api/users", json=payload, headers=auth_headers(staff_user)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_prevent_last_admin_deactivation(client, admin_user):
    """Cannot deactivate the only active admin in the system."""
    payload = {
        "is_active": False,
    }
    response = await client.put(
        f"/api/users/{admin_user.id}",
        json=payload,
        headers=auth_headers(admin_user),
    )
    assert response.status_code in (400, 422, 403)


@pytest.mark.asyncio
async def test_search_users(client, admin_user, db_session):
    """Search by name or email works."""
    extra = User(
        name="UniqueSearchableName",
        email="uniquesearch@example.com",
        password_hash=hash_password("password123"),
        role="staff",
        is_active=True,
    )
    db_session.add(extra)
    await db_session.flush()

    response = await client.get(
        "/api/users?search=UniqueSearchable", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert any("uniquesearch" in u["email"] for u in data["users"])


@pytest.mark.asyncio
async def test_filter_users_by_role(client, admin_user, staff_user):
    """Role filter works."""
    response = await client.get(
        "/api/users?role=staff", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert all(u["role"] == "staff" for u in data["users"])
    assert any(u["id"] == staff_user.id for u in data["users"])


@pytest.mark.asyncio
async def test_pagination(client, admin_user, db_session):
    """Pagination returns correct metadata."""
    for i in range(15):
        user = User(
            name=f"Paginated User {i}",
            email=f"pageuser{i}@test.com",
            password_hash=hash_password("password123"),
            role="staff",
            is_active=True,
        )
        db_session.add(user)
    await db_session.flush()

    response = await client.get(
        "/api/users?page=1&per_page=5", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) == 5
    assert data["pagination"]["page"] == 1
    assert data["pagination"]["per_page"] == 5
    assert data["pagination"]["total"] >= 16
