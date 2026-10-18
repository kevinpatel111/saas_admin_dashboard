from decimal import Decimal
import pytest
from app.features.categories.models import Category
from app.features.products.models import Product
from tests.conftest import auth_headers


@pytest.fixture
async def sample_category(db_session):
    cat = Category(name="Electronics", description="Electronic gadgets")
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest.fixture
async def sample_product(db_session, sample_category):
    prod = Product(
        name="Laptop Pro",
        sku="LAP-001",
        description="High-end laptop",
        price=Decimal("1299.99"),
        stock_quantity=25,
        category_id=sample_category.id,
        status="active",
    )
    db_session.add(prod)
    await db_session.flush()
    return prod


@pytest.mark.asyncio
async def test_create_product(client, admin_user, sample_category):
    """POST /api/products creates product."""
    payload = {
        "name": "Wireless Mouse",
        "sku": "MOU-001",
        "description": "Ergonomic wireless mouse",
        "price": 29.99,
        "stock_quantity": 100,
        "category_id": sample_category.id,
        "status": "active",
    }
    response = await client.post(
        "/api/products", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code in (200, 201)
    data = response.json()
    assert data["sku"] == "MOU-001"
    assert data["name"] == "Wireless Mouse"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_product_duplicate_sku(client, admin_user, sample_product):
    """Duplicate SKU returns 409."""
    payload = {
        "name": "Another Laptop",
        "sku": sample_product.sku,
        "price": 999.00,
        "stock_quantity": 5,
        "category_id": sample_product.category_id,
        "status": "active",
    }
    response = await client.post(
        "/api/products", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_products(client, admin_user, sample_product):
    """GET /api/products returns list."""
    response = await client.get("/api/products", headers=auth_headers(admin_user))
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert any(p["sku"] == sample_product.sku for p in data["products"])


@pytest.mark.asyncio
async def test_update_product(client, admin_user, sample_product):
    """PUT /api/products/{id} updates product."""
    payload = {
        "name": "Laptop Pro Max",
        "price": 1499.99,
    }
    response = await client.put(
        f"/api/products/{sample_product.id}",
        json=payload,
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Laptop Pro Max"
    assert float(data["price"]) == 1499.99


@pytest.mark.asyncio
async def test_delete_product(client, admin_user, sample_product):
    """DELETE /api/products/{id} deletes product."""
    response = await client.delete(
        f"/api/products/{sample_product.id}",
        headers=auth_headers(admin_user),
    )
    assert response.status_code in (200, 204)

    get_res = await client.get(
        f"/api/products/{sample_product.id}",
        headers=auth_headers(admin_user),
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_filter_by_category(client, admin_user, sample_product, db_session):
    """Category filter works."""
    other_cat = Category(name="Books", description="Literature")
    db_session.add(other_cat)
    await db_session.flush()

    other_prod = Product(
        name="Python Handbook",
        sku="BOK-001",
        price=Decimal("45.00"),
        stock_quantity=50,
        category_id=other_cat.id,
        status="active",
    )
    db_session.add(other_prod)
    await db_session.flush()

    response = await client.get(
        f"/api/products?category_id={sample_product.category_id}",
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert all(p["category_id"] == sample_product.category_id for p in data["products"])


@pytest.mark.asyncio
async def test_invalid_price(client, admin_user):
    """Negative price returns 422."""
    payload = {
        "name": "Invalid Price Item",
        "sku": "INV-001",
        "price": -10.50,
        "stock_quantity": 10,
    }
    response = await client.post(
        "/api/products", json=payload, headers=auth_headers(admin_user)
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_staff_cannot_create_product(client, staff_user):
    """Staff gets 403 when creating a product."""
    payload = {
        "name": "Unauthorized Product",
        "sku": "UNAUTH-001",
        "price": 100.00,
        "stock_quantity": 10,
    }
    response = await client.post(
        "/api/products", json=payload, headers=auth_headers(staff_user)
    )
    assert response.status_code == 403
