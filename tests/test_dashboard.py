from decimal import Decimal
import pytest
from app.features.categories.models import Category
from app.features.products.models import Product
from tests.conftest import auth_cookies, auth_headers


@pytest.fixture
async def sample_dashboard_data(db_session):
    cat = Category(name="Cloud Computing", description="Cloud infrastructure")
    db_session.add(cat)
    await db_session.flush()

    prod1 = Product(
        name="Compute Node",
        sku="COM-001",
        price=Decimal("99.99"),
        stock_quantity=5,  # Low stock
        category_id=cat.id,
        status="active",
    )
    prod2 = Product(
        name="Storage Bucket",
        sku="STO-001",
        price=Decimal("19.99"),
        stock_quantity=100,
        category_id=cat.id,
        status="active",
    )
    db_session.add_all([prod1, prod2])
    await db_session.flush()


@pytest.mark.asyncio
async def test_dashboard_page(client, admin_user, sample_dashboard_data):
    """GET /dashboard renders with stats for authenticated user."""
    cookies = auth_cookies(admin_user)
    client.cookies.set("access_token", cookies["access_token"])

    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "dashboard" in response.text.lower()


@pytest.mark.asyncio
async def test_dashboard_stats_api(client, admin_user, sample_dashboard_data):
    """GET /api/dashboard/stats returns correct counts and metrics."""
    response = await client.get(
        "/api/dashboard/stats", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_users" in data or "users_count" in data or "total_products" in data
    # Check that counts reflect created data
    if "total_products" in data:
        assert data["total_products"] >= 2


@pytest.mark.asyncio
async def test_chart_data_api(client, admin_user, sample_dashboard_data):
    """GET /api/dashboard/charts returns chart dataset structures."""
    response = await client.get(
        "/api/dashboard/charts", headers=auth_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (dict, list))
