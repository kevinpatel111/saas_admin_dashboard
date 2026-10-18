import pytest
from app.core.security import generate_csrf_token, hash_password
from app.features.users.models import User
from tests.conftest import auth_cookies, auth_headers


@pytest.mark.asyncio
async def test_login_page_renders(client):
    """GET /login returns 200 and renders HTML login form."""
    response = await client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "login" in response.text.lower()


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    """POST /login with valid credentials sets cookies and redirects to /dashboard."""
    csrf_token = generate_csrf_token()
    client.cookies.set("csrf_token", csrf_token)

    response = await client.post(
        "/login",
        data={
            "email": "admin@test.com",
            "password": "admin12345",
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    # Check redirect status
    assert response.status_code in (302, 303)
    assert response.headers.get("location") == "/dashboard"
    # Ensure access_token cookie is set
    assert "access_token" in response.cookies or "access_token" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_login_invalid_password(client, admin_user):
    """POST /login with wrong password shows error message."""
    csrf_token = generate_csrf_token()
    client.cookies.set("csrf_token", csrf_token)

    response = await client.post(
        "/login",
        data={
            "email": "admin@test.com",
            "password": "wrongpassword",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code in (200, 400, 401)
    assert "invalid" in response.text.lower() or "error" in response.text.lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """POST /login with unknown email shows error."""
    csrf_token = generate_csrf_token()
    client.cookies.set("csrf_token", csrf_token)

    response = await client.post(
        "/login",
        data={
            "email": "nonexistent@test.com",
            "password": "somepassword123",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code in (200, 400, 401)
    assert "invalid" in response.text.lower() or "error" in response.text.lower()


@pytest.mark.asyncio
async def test_login_inactive_user(client, db_session):
    """Inactive user cannot login."""
    inactive = User(
        name="Inactive User",
        email="inactive@test.com",
        password_hash=hash_password("inactive123"),
        role="staff",
        is_active=False,
    )
    db_session.add(inactive)
    await db_session.flush()

    csrf_token = generate_csrf_token()
    client.cookies.set("csrf_token", csrf_token)

    response = await client.post(
        "/login",
        data={
            "email": "inactive@test.com",
            "password": "inactive123",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )
    assert response.status_code in (200, 400, 401, 403)
    assert "inactive" in response.text.lower() or "error" in response.text.lower() or "invalid" in response.text.lower()


@pytest.mark.asyncio
async def test_api_login_success(client, admin_user):
    """POST /api/auth/login returns token JSON with access_token."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "admin12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_api_login_failure(client, admin_user):
    """POST /api/auth/login with wrong password returns 401."""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout(client, admin_user):
    """GET /logout clears cookies and redirects to /login."""
    cookies = auth_cookies(admin_user)
    client.cookies.set("access_token", cookies["access_token"])

    response = await client.get("/logout", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers.get("location") == "/login"


@pytest.mark.asyncio
async def test_protected_route_without_auth(client):
    """GET /dashboard without token redirects to /login."""
    response = await client.get("/dashboard", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers.get("location") == "/login"


@pytest.mark.asyncio
async def test_protected_api_without_auth(client):
    """GET /api/users without token returns 401."""
    response = await client.get("/api/users")
    assert response.status_code == 401
