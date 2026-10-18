# SaaS Admin Dashboard

A robust, production-grade SaaS Admin Dashboard built with FastAPI, Python, SQLAlchemy (async), MySQL, and Bootstrap 5. Designed with clean three-layer architecture (Route → Service/Logic → Repository/Data), comprehensive role-based access control (RBAC), and security-first defaults.

---

## Architecture Overview

The system strictly decouples presentation, domain logic, and data storage:

```
+-------------------------------------------------------------------+
|                        HTTP / Client Request                      |
|          (Browser Session / Cookie or REST API Bearer JWT)        |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                     Presentation & Route Layer                    |
|  - app/features/*/routes.py (FastAPI routers, cookie/token checks)|
|  - Dependency injection: get_db, get_current_user, require_role   |
|  - CSRF validation middleware & token checks on mutations         |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    Service & Domain Logic Layer                   |
|  - app/features/*/service.py                                      |
|  - Business constraints (e.g. role rules, prevent last admin del) |
|  - Password hashing & verification, token generation              |
|  - CSV export generation & analytics aggregation                  |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                    Data & Repository Layer                        |
|  - app/features/*/repository.py                                   |
|  - SQLAlchemy 2.0 Async ORM queries                               |
|  - Pagination, filtering, searching                               |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                         MySQL Database                            |
|             (or in-memory Async SQLite during tests)              |
+-------------------------------------------------------------------+
```

---

## Tech Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+), [Uvicorn](https://www.uvicorn.org/)
- **Database ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) (Asyncio) with `aiomysql` driver
- **Migrations:** [Alembic](https://alembic.sqlalchemy.org/) (Async migrations)
- **Frontend / UI:** [Jinja2](https://jinja.palletsprojects.com/) Templates, [Bootstrap 5](https://getbootstrap.com/), Chart.js
- **Auth & Security:** JWT (`pyjwt`), Password Hashing (`passlib[bcrypt]`), HMAC CSRF tokens, HttpOnly cookies
- **Testing:** [pytest](https://docs.pytest.org/), `pytest-asyncio`, `httpx` (AsyncClient), `aiosqlite`
- **Containerization:** Docker & Docker Compose

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/) (recommended for containerized execution)
- Alternatively, Python 3.12+ and a running MySQL 8 instance for native execution.

---

## Quick Start (Docker Compose)

1. **Clone the repository and enter directory:**

   ```bash
   cd saas_admin_dashboard
   ```

2. **Configure environment:**
   Copy `.env.example` to `.env`:

   ```bash
   cp .env.example .env
   ```

3. **Start services:**

   ```bash
   docker compose up --build -d
   ```

4. **Run migrations:**

   ```bash
   docker compose exec app alembic upgrade head
   ```

5. **Create initial admin account:**

   ```bash
   docker compose exec -it app python -m scripts.create_admin
   ```

6. **Access application:**
   - Web Dashboard: [http://localhost:8000](http://localhost:8000)
   - Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   - Alternative API Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Manual Setup (Without Docker)

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Create a `.env` file from `.env.example`:

   ```ini
   APP_NAME=SaaS Admin Dashboard
   DEBUG=True
   DATABASE_URL=mysql+aiomysql://saas_user:saas_password@localhost:3306/saas_dashboard
   SECRET_KEY=your-super-secret-key-change-in-production
   CSRF_SECRET=your-csrf-secret-key-change-in-production
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   ```

4. **Ensure MySQL is running:**
   Create database and grant permissions:

   ```sql
   CREATE DATABASE saas_dashboard CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'saas_user'@'localhost' IDENTIFIED BY 'saas_password';
   GRANT ALL PRIVILEGES ON saas_dashboard.* TO 'saas_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

5. **Run database migrations:**

   ```bash
   alembic upgrade head
   ```

6. **Create an admin user:**

   ```bash
   python scripts/create_admin.py
   ```

7. **Run development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## Database Migrations (Alembic)

- **Create a new migration after model changes:**
  ```bash
  alembic revision --autogenerate -m "describe_changes"
  ```
- **Apply migrations:**
  ```bash
  alembic upgrade head
  ```
- **Roll back one migration:**
  ```bash
  alembic downgrade -1
  ```

---

## Running Tests

The test suite runs against an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`) using isolated transactions rolled back after each test case.

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

Run a specific test module:

```bash
pytest tests/test_auth.py -v
```

---

## Project Structure

```text
saas_admin_dashboard/
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── compose.yaml
├── pytest.ini
├── README.md
├── requirements.txt
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── exceptions.py
│   ├── logging_config.py
│   ├── core/
│   │   ├── dependencies.py
│   │   ├── permissions.py
│   │   └── security.py
│   └── features/
│       ├── auth/
│       ├── categories/
│       ├── dashboard/
│       ├── products/
│       ├── reports/
│       └── users/
├── scripts/
│   └── create_admin.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_auth.py
    ├── test_categories.py
    ├── test_dashboard.py
    ├── test_products.py
    └── test_users.py
```

---

## Security Features

- **Role-Based Access Control (RBAC):** Hierarchical roles (`admin` > `manager` > `staff`) enforced through dependency guards (`require_role`).
- **CSRF Protection:** State-changing requests (POST, PUT, DELETE) verified with signed HMAC tokens in both form submissions and headers.
- **Secure Password Hashing:** Bcrypt hashing with salted passwords via Passlib.
- **JWT & Session Security:** Signed JWTs stored in secure, `HttpOnly` cookies for web sessions or `Authorization: Bearer` headers for API consumers.
- **SQL Injection Prevention:** 100% parameterized queries via SQLAlchemy 2.0 ORM expressions.
- **Docker Security:** Runs under an unprivileged `app` non-root system user.

---

## Deployment Notes

- Set `DEBUG=False` in production environments.
- Provide cryptographically secure values for `SECRET_KEY` and `CSRF_SECRET` (generate using `openssl rand -hex 32` or `python -c "import secrets; print(secrets.token_hex(32))"`).
- Place application behind a TLS-terminating reverse proxy (e.g. Nginx, Caddy, Cloudflare, AWS ALB).
- Use health check endpoints `/api/health` to monitor service uptime in container orchestrators.

---

## License

This project is licensed under the [MIT License](LICENSE).

Role Email Password Permissions
Admin admin@example.com admin12345 Full system access (Users, RBAC, Categories, Products, Reports, CSV Exports)
Manager manager@example.com manager12345 Manage categories, products, and reports
Staff staff@example.com staff12345 Read products & update stock
