import asyncio
import sys
from pathlib import Path

# Ensure root folder is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.features.users.models import User
from app.features.categories.models import Category
from app.features.products.models import Product
from app.core.security import hash_password


async def seed_data():
    async with AsyncSessionLocal() as session:
        # 1. Seed Users if not present
        existing_admin = await session.execute(select(User).where(User.email == "admin@example.com"))
        if not existing_admin.scalar_one_or_none():
            users = [
                User(
                    name="System Administrator",
                    email="admin@example.com",
                    password_hash=hash_password("admin12345"),
                    role="admin",
                    is_active=True,
                ),
                User(
                    name="Operations Manager",
                    email="manager@example.com",
                    password_hash=hash_password("manager12345"),
                    role="manager",
                    is_active=True,
                ),
                User(
                    name="Support Staff",
                    email="staff@example.com",
                    password_hash=hash_password("staff12345"),
                    role="staff",
                    is_active=True,
                ),
                User(
                    name="Sarah Connor",
                    email="sarah.connor@example.com",
                    password_hash=hash_password("password123"),
                    role="staff",
                    is_active=True,
                ),
                User(
                    name="Alex Rivera",
                    email="alex.rivera@example.com",
                    password_hash=hash_password("password123"),
                    role="manager",
                    is_active=False,
                ),
            ]
            session.add_all(users)
            await session.commit()
            print("[+] Seeded demo users (admin@example.com: admin12345)")

        # 2. Seed Categories
        existing_cat = await session.execute(select(Category))
        categories = existing_cat.scalars().all()
        if not categories:
            cat_objs = [
                Category(name="Cloud Computing", description="Cloud VMs, serverless runtimes, and cluster instances"),
                Category(name="AI & Analytics", description="Managed LLM inference, embedding models, and data pipelines"),
                Category(name="Database Services", description="Managed SQL, NoSQL, and vector memory engines"),
                Category(name="Developer Tooling", description="CI/CD pipelines, code scanners, and staging preview nodes"),
                Category(name="Cybersecurity", description="Zero-trust proxies, WAF protection, and identity vaults"),
            ]
            session.add_all(cat_objs)
            await session.commit()
            
            # Re-fetch with IDs
            res = await session.execute(select(Category))
            categories = list(res.scalars().all())
            print(f"[+] Seeded {len(categories)} product categories")

        # 3. Seed Products
        existing_prod = await session.execute(select(Product))
        if not existing_prod.scalars().first():
            cat_map = {c.name: c.id for c in categories}
            now = datetime.now(timezone.utc)

            products = [
                Product(
                    name="High-Compute GPU Instance",
                    sku="COMP-GPU-01",
                    description="NVIDIA H100 GPU instance with 80GB VRAM",
                    price=Decimal("499.00"),
                    stock_quantity=4,  # Low stock
                    category_id=cat_map.get("Cloud Computing"),
                    status="active",
                    created_at=now - timedelta(days=90),
                ),
                Product(
                    name="Serverless Application Runner",
                    sku="SRV-RUN-02",
                    description="Auto-scaling container runtime engine with HTTP trigger",
                    price=Decimal("49.99"),
                    stock_quantity=150,
                    category_id=cat_map.get("Cloud Computing"),
                    status="active",
                    created_at=now - timedelta(days=60),
                ),
                Product(
                    name="Managed PostgreSQL Cluster",
                    sku="DB-PG-01",
                    description="High availability PostgreSQL with automated read replicas",
                    price=Decimal("129.50"),
                    stock_quantity=8,  # Low stock
                    category_id=cat_map.get("Database Services"),
                    status="active",
                    created_at=now - timedelta(days=45),
                ),
                Product(
                    name="Vector Index Cache Service",
                    sku="VEC-MEM-04",
                    description="In-memory HNSW similarity index for semantic search",
                    price=Decimal("89.00"),
                    stock_quantity=22,
                    category_id=cat_map.get("Database Services"),
                    status="active",
                    created_at=now - timedelta(days=30),
                ),
                Product(
                    name="LLM Inference Gateway",
                    sku="AI-GATE-01",
                    description="Unified multi-provider AI model routing and rate limiting",
                    price=Decimal("199.00"),
                    stock_quantity=3,  # Low stock
                    category_id=cat_map.get("AI & Analytics"),
                    status="active",
                    created_at=now - timedelta(days=20),
                ),
                Product(
                    name="Fine-Tuning Worker Node",
                    sku="AI-FINE-02",
                    description="LoRA and full checkpoint fine-tuning runner",
                    price=Decimal("350.00"),
                    stock_quantity=18,
                    category_id=cat_map.get("AI & Analytics"),
                    status="active",
                    created_at=now - timedelta(days=15),
                ),
                Product(
                    name="Zero-Trust Edge Tunnel",
                    sku="SEC-TUN-01",
                    description="Encrypted wireguard mesh gateway for internal microservices",
                    price=Decimal("39.00"),
                    stock_quantity=250,
                    category_id=cat_map.get("Cybersecurity"),
                    status="active",
                    created_at=now - timedelta(days=10),
                ),
                Product(
                    name="Automated Vulnerability Scanner",
                    sku="SEC-SCAN-02",
                    description="Continuous dependency, container image and SAST inspection",
                    price=Decimal("79.99"),
                    stock_quantity=5,  # Low stock
                    category_id=cat_map.get("Cybersecurity"),
                    status="active",
                    created_at=now - timedelta(days=5),
                ),
                Product(
                    name="CI/CD Build Runner 4-Core",
                    sku="DEV-RUN-01",
                    description="Ephemeral Linux build runner with cached Docker layers",
                    price=Decimal("29.00"),
                    stock_quantity=80,
                    category_id=cat_map.get("Developer Tooling"),
                    status="active",
                    created_at=now - timedelta(days=2),
                ),
                Product(
                    name="Staging Environment Pod",
                    sku="DEV-STG-02",
                    description="Preview branch ephemeral deployment with dynamic DNS",
                    price=Decimal("19.00"),
                    stock_quantity=60,
                    category_id=cat_map.get("Developer Tooling"),
                    status="active",
                    created_at=now,
                ),
            ]
            session.add_all(products)
            await session.commit()
            print(f"[+] Seeded {len(products)} demo products with stock and category relationships")

    print("\n[+] Demo database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
