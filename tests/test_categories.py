from decimal import Decimal
import pytest
from app.features.categories.models import Category
from app.features.products.models import Product
from tests.conftest import auth_headers


@pytest.fixture
async def sample_category(db_session):
    cat = Category(name="Office Supplies", description="Paper, pens, desks")
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest.mark.asyncio
async def test_create_category(client, admin_user):
    """POST /api/categories creates a new category."""
    payload = {
        "name": "Hardware",
        "description": "Hardware tools and parts",
    }
    response = await client.post(
        "/api/categories", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["name"] == "Hardware"
    assert "id" in data


@pytest.mark.asyncio
async def test_duplicate_category_name(client, admin_user, sample_category):
    """Creating duplicate category name returns 409."""
    payload = {
        "name": sample_category.name,
        "description": "Duplicate category",
    }
    response = await client.post(
        "/api/categories", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_category_with_products(client, admin_user, sample_category, db_session):
    """Deleting a category that has attached products returns an error."""
    prod = Product(
        name="Ballpoint Pen",
        sku="PEN-001",
        price=Decimal("1.99"),
        stock_quantity=500,
        category_id=sample_category.id,
        status="active",
    )
    db_session.add(prod)
    await db_session.flush()

    response = await client.delete(
        f"/api/categories/{sample_category.id}",
        headers=auth_headers(admin_user),
    )
    assert response.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_delete_empty_category(client, admin_user, db_session):
    """Deleting an empty category succeeds."""
    cat = Category(name="Empty Category", description="No products here")
    db_session.add(cat)
    await db_session.flush()

    response = await client.delete(
        f"/api/categories/{cat.id}",
        headers=auth_headers(admin_user),
    )
    assert response.status_code in (200, 204)

    get_res = await client.get(
        f"/api/categories/{cat.id}",
        headers=auth_headers(admin_user),
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_list_categories(client, admin_user, sample_category):
    """GET /api/categories returns category list with product counts."""
    response = await client.get("/api/categories", headers=auth_headers(admin_user))
    assert response.status_code == 200
    data = response.json()
    categories_list = data.get("categories", data) if isinstance(data, dict) else data
    assert any(c["id"] == sample_category.id for c in categories_list)
    assert "product_count" in categories_list[0]
