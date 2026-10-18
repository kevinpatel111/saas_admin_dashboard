import asyncio
import getpass
import sys
from pathlib import Path

# Ensure root folder is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.features.users.models import User
from app.core.security import hash_password

async def create_admin():
    if len(sys.argv) >= 4:
        name = sys.argv[1].strip()
        email = sys.argv[2].strip().lower()
        password = sys.argv[3]
    else:
        name = input("Admin name: ").strip()
        email = input("Admin email: ").strip().lower()
        password = getpass.getpass("Admin password (min 8 chars): ")
        if len(password) < 8:
            print("Error: Password must be at least 8 characters")
            sys.exit(1)
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Error: Passwords do not match")
            sys.exit(1)

    if len(password) < 8:
        print("Error: Password must be at least 8 characters")
        sys.exit(1)
    
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"Error: User with email {email} already exists")
            sys.exit(1)
        user = User(name=name, email=email, password_hash=hash_password(password), role="admin", is_active=True)
        session.add(user)
        await session.commit()
        print(f"Admin user '{name}' ({email}) created successfully!")

if __name__ == "__main__":
    asyncio.run(create_admin())
