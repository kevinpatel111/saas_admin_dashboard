import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.features.users.models import User
from app.features.categories.models import Category
from app.features.products.models import Product

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
async_session_test = async_sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    connection = await engine_test.connect()
    transaction = await connection.begin()
    session = async_session_test(bind=connection)
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()

@pytest_asyncio.fixture
async def client(db_session):
    from app.main import app
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(name="Admin", email="admin@test.com", password_hash=hash_password("admin12345"), role="admin", is_active=True)
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def manager_user(db_session):
    user = User(name="Manager", email="manager@test.com", password_hash=hash_password("manager123"), role="manager", is_active=True)
    db_session.add(user)
    await db_session.flush()
    return user

@pytest_asyncio.fixture
async def staff_user(db_session):
    user = User(name="Staff", email="staff@test.com", password_hash=hash_password("staff12345"), role="staff", is_active=True)
    db_session.add(user)
    await db_session.flush()
    return user

def auth_headers(user):
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

def auth_cookies(user):
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token}
