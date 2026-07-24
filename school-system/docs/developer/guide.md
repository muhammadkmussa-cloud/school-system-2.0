# School Management System — Developer Guide

## Architecture Philosophy

School Management System follows a **layered architecture** with strict separation of concerns:

```
API Layer (FastAPI routes)
  ↓  calls
Service Layer (business logic)
  ↓  uses
Repository Layer (data access)
  ↓  queries
Database (PostgreSQL)
```

**Rules:**
- API routes are **thin** — they validate input, call services, return responses
- Services contain **all business logic** — grading, promotion, analytics
- Models are **pure data** — no business logic in ORM models
- Every query is **school-scoped** — `school_id` filter on every read/write

---

## Project Structure

```
backend/app/
├── api/
│   ├── v1/              # Internal REST API (25 modules)
│   ├── mobile/          # Mobile-optimized compact endpoints
│   └── public/          # Third-party API gateway (API key auth)
├── core/                # Config, security, database, RBAC
├── middleware/           # Multi-tenancy context
├── models/              # SQLAlchemy ORM (19 entities)
├── schemas/             # Pydantic request/response models
├── services/            # Business logic (20 services)
│   ├── assignments/
│   ├── audit/
│   ├── calendar/
│   ├── curriculum/
│   ├── dashboard/
│   ├── exam/
│   ├── imports/
│   ├── notifications/
│   ├── reports/
│   └── sync/
├── tasks/               # Celery jobs & scheduler
└── utils/               # Error handlers
```

---

## Adding a New Feature

### 1. Define the model

```python
# app/models/my_feature.py
class MyFeature(Base, TimestampMixin):
    __tablename__ = "my_features"
    school_id: Mapped[uuid.UUID] = ...  # ← ALWAYS include this
    name: Mapped[str] = ...
```

### 2. Create the service

```python
# app/services/my_feature_service.py
class MyFeatureService:
    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def create(self, data: dict) -> MyFeature:
        # ALL queries filter by self.school_id
        ...
```

### 3. Add the API route

```python
# app/api/v1/my_feature.py
from app.core.rbac import require_permission

@router.post("")
async def create(payload: MySchema, db: DB, current_user: RequireStaff):
    svc = MyFeatureService(db, current_user.school_id)
    return await svc.create(payload)
```

### 4. Register in v1 router

```python
# app/api/v1/__init__.py
router.include_router(my_feature.router, prefix="/my-feature", tags=["My Feature"])
```

### 5. Add permissions

```python
# app/core/rbac.py — add to ROLES dict
# app/core/rbac_enforcer.py — add to RBAC_ROUTE_MAP
```

### 6. Add tests

```python
# tests/test_my_feature.py
# tests/integration/test_my_feature_workflow.py
```

---

## Security Checklist (per endpoint)

- [ ] `school_id` filter on every database query
- [ ] RBAC dependency injection (`RequireStaff`, etc.)
- [ ] Pydantic schema validates all inputs
- [ ] No raw SQL without parameterization
- [ ] Audit log for mutations (create/update/delete)
- [ ] Proper HTTP status codes (201 for create, 204 for delete)

---

## Running Locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL
alembic upgrade head
python -m app.seed --reset   # demo data
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

---

## Running Tests

```bash
# Unit tests
pytest tests/ -v

# Specific test file
pytest tests/test_rbac.py -v

# Integration tests (require aiosqlite)
pip install aiosqlite
pytest tests/integration/ -v

# With coverage
pip install pytest-cov
pytest tests/ --cov=app --cov-report=html
```

---

## Running Benchmarks

```bash
python -m benchmarks.bench_runner --students 1000 --marks 500
```

---

## Running Security Audit

```bash
python -m scripts.security_audit
```

---

## Database Migrations

```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "add_my_feature_table"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Celery Tasks

```bash
# Start worker
celery -A app.tasks.celery_app worker --loglevel=info

# Start beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info

# Run a specific task manually
python -c "from app.tasks.jobs import daily_health_check; daily_health_check.delay()"
```

---

## Multi-Tenancy Rules

1. Every model that belongs to a school has a `school_id` column
2. Every query on school-scoped models includes `WHERE school_id = ?`
3. Platform admins (`role == "platform_admin"`) bypass school scoping
4. JWT payload carries `school_id` — extracted by `SchoolContextMiddleware`
5. Never trust `school_id` from request body — always use JWT

---

## Grading System

The platform uses the Kenyan KCSE 12-point scale by default:

| Grade | Range | Points |
|-------|-------|--------|
| A | 80-100% | 12 |
| A- | 75-79% | 11 |
| B+ | 70-74% | 10 |
| B | 65-69% | 9 |
| B- | 60-64% | 8 |
| C+ | 55-59% | 7 |
| C | 50-54% | 6 |
| C- | 45-49% | 5 |
| D+ | 40-44% | 4 |
| D | 35-39% | 3 |
| D- | 30-34% | 2 |
| E | 0-29% | 1 |

To use a different grading scheme, assign a different curriculum to the school via `POST /api/v1/curriculum/assign`.

---

## RBAC Matrix

| Role | Level | Key Permissions |
|------|-------|----------------|
| platform_admin | 100 | Everything (`*:*`) |
| school_admin | 80 | students:CRUD, teachers:CRUD, settings:manage, reports:export |
| deputy_principal | 70 | reports:view/export, analytics:view, students:promote |
| head_teacher | 60 | exams:manage, timetable:manage, students:promote |
| class_teacher | 40 | attendance:write, marks:write (own class) |
| subject_teacher | 30 | marks:write, lessons:write (own subjects) |
| teacher | 20 | attendance:write, marks:write, lessons:write |

---

## API Versioning

- Current: `v1` at `/api/v1/`
- Public API: `/public/v1/` (API key auth, rate-limited)
- Mobile API: `/api/v1/mobile/` (compact payloads, delta sync)
- Breaking changes get a new version (`v2`)
- Deprecated versions supported for 6 months
