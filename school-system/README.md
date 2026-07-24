# School Management System

**Teacher-Centred School Management Platform for Africa**

School Management System is a production-grade, multi-tenant, cloud-based school management
SaaS designed to simplify teachers' daily work.  It provides centralized
attendance, timetables, grading, lesson planning, reporting, exam management,
curriculum configuration, workflow automation, and offline-first sync — all
with role-based access control and comprehensive audit logging.

**159 source files · 33 API modules · 19 database models · 21 business services
· 12 test suites · 6 curricula · 4 approval workflows**

---

## Architecture

```
school-system/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/          # 27 REST modules (internal API)
│   │   │   ├── mobile/      # Mobile-optimized compact endpoints
│   │   │   └── public/      # Third-party API gateway (API-key auth)
│   │   ├── core/            # Config, security, database, RBAC, enforcer
│   │   ├── middleware/       # Multi-tenancy context middleware
│   │   ├── models/          # 19 SQLAlchemy ORM entities
│   │   ├── schemas/         # Pydantic request/response models
│   │   ├── services/        # 21 business-logic services
│   │   │   ├── assignments/    calendar/    curriculum/
│   │   │   ├── dashboard/      edge_cases/  exam/
│   │   │   ├── imports/        notifications/  reports/
│   │   │   ├── sync/           audit/       workflow/
│   │   │   ├── analytics_service.py
│   │   │   ├── auth_service.py
│   │   │   ├── promotion_service.py
│   │   │   └── results_engine.py
│   │   ├── tasks/            # Celery async jobs + beat scheduler
│   │   └── utils/            # Error handlers
│   ├── alembic/              # Database migrations
│   ├── benchmarks/           # Performance benchmark suite
│   ├── scripts/              # Security audit + tools
│   └── tests/                # 12 suites (unit + integration + e2e)
├── frontend/
│   └── src/
│       ├── pages/            # 15 route pages (one per module)
│       ├── features/         # 6 rich feature components
│       ├── components/       # Layout + shared components
│       ├── services/         # Axios client with interceptors
│       ├── store/            # Zustand state management
│       └── types/            # TypeScript interfaces
├── deploy/                   # NGINX + systemd production configs
├── docs/                     # API reference + deployment + developer guides
├── docker-compose.yml        # Full-stack orchestration
└── .github/workflows/        # CI/CD pipeline
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local dev)
- Node.js 20+ (for frontend dev)
- PostgreSQL 16+ (if running without Docker)

### Docker (recommended)

```bash
git clone https://github.com/your-org/school-system.git
cd school-system
docker compose up -d

# Seed demo data (school + 160 students + 8 teachers + timetable + marks)
docker compose exec api python -m app.seed --reset

# Frontend → http://localhost:5173
# API docs → http://localhost:8000/docs
# Public API → http://localhost:8000/public/v1/
```

### Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed --reset
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
pip install aiosqlite pytest-cov
pytest tests/ -v --cov=app

# Security audit
python -m scripts.security_audit

# Benchmarks
python -m benchmarks.bench_runner --students 500 --marks 200
```

---

## Login Credentials (Seed Data)

| Role | Email | Password |
|------|-------|----------|
| Platform Admin | `platform@example.com` | `admin123` |
| School Admin | `admin@example.com` | `admin123` |
| Teacher | Any teacher email from seed | `teacher123` |

---

## API Modules (33 total)

| Module | Description |
|--------|-------------|
| `/auth` | Login, refresh tokens, change-password, logout, me |
| `/users` | User CRUD with school isolation |
| `/schools` | Multi-tenant school management, suspend/activate |
| `/students` | Student profiles, search, transfer, promote, archive |
| `/teachers` | Teacher accounts, activation/deactivation |
| `/academic` | Years, terms, classes, streams, subjects, departments |
| `/timetable` | Timetable with conflict detection |
| `/attendance` | Batch recording, stats, history |
| `/gradebook` | Assessments, marks, grade distribution, stats |
| `/lessons` | Lesson planning, duplication, completion tracking |
| `/results` | Report cards (JSON + PDF), class rankings, summaries |
| `/exams` | Exam series, papers, scores, ranking, aggregation |
| `/reports` | CSV/PDF exports for all report types |
| `/analytics` | Attendance trends, gender analysis, syllabus coverage |
| `/dashboard` | Admin + teacher dashboard widgets |
| `/dashboard/advanced` | Executive summary, heatmaps, at-risk, leaderboard |
| `/curriculum` | 6 configurable curricula (CBC, 8-4-4, Cambridge, IB…) |
| `/workflow` | Approval chains (report cards, exams, promotion) |
| `/audit` | Immutable audit trail with search + entity history |
| `/imports` | Bulk CSV import (students, teachers, marks) + templates |
| `/promotion` | Bulk promote, retain-by-mean, rollback, promotion paths |
| `/assignments` | Digital homework/classwork with submission tracking |
| `/calendar` | Weekly timetable + iCalendar (ICS) feed |
| `/notifications` | Multi-channel: email, SMS, in-app, push |
| `/push` | FCM push notification registration + sending |
| `/sync` | Offline-first sync protocol (last-write-wins) |
| `/health/full` | Production health check: DB, Redis, Celery, storage |
| `/mobile/*` | Compact endpoints for Flutter: today, quick-attendance, quick-marks, delta-sync |

---

## Key Features

### Security
- Argon2id password hashing (GPU-resistant, memory-hard)
- Dual-token JWT (short-lived access + revocable refresh)
- 7-tier role-based access control with 60+ granular permissions
- Automatic session timeout + login attempt lockout
- Refresh token rotation with reuse detection
- Automated security audit script

### Multi-Tenancy
- Every record isolated by `school_id`
- Platform admins operate across all schools
- Middleware extracts school context from JWT on every request
- `BaseRepository` auto-filters queries — impossible to forget scoping

### Curriculum Abstraction
6 pre-loaded, configurable curricula — same codebase serves any country:
- 🇰🇪 CBC Kenya (Grade 1→12) · 🇰🇪 8-4-4 KCSE (Std 1→F4)
- 🌍 Cambridge IGCSE (Y7→13) · 🌍 IB Diploma (DP1→2)
- 🇳🇬 Nigeria BEC/WAEC (P1→SSS3) · 🇿🇦 South Africa CAPS (Grade R→12)

Each curriculum defines levels, progression paths, and grading bands.
Schools switch curricula at runtime — no code changes.

### Results Engine
- Per-student cumulative grading across weighted assessments
- Automatic grade letter + points (configurable per curriculum)
- Class rankings with tie-breaking · Class-wide performance summaries
- A4 PDF report cards with school header, subject table, teacher/principal remarks

### Workflow Automation
4 built-in approval state machines:
- Report Card: draft → head → principal → approved → published
- Exam Publishing: draft → moderation → moderated → published
- Student Promotion: proposed → approval → approved/rejected
- Attendance Lock: open → locked

### Offline-First Sync
- Attendance + marks flagged with `synced` boolean
- Last-write-wins conflict resolution on (student, date) keys
- Delta-sync protocol: clients push changes + pull server updates
- Ready for Flutter mobile client with Isar local DB

---

## Test Suite

| Type | Files | Coverage |
|------|-------|----------|
| Security | `test_security.py` | Argon2 hashing, JWT encode/decode, expiry |
| Results | `test_results_engine.py` | All 12 KCSE grade boundaries, edge cases |
| Edge Cases | `test_edge_cases.py` | Tie-breaking, clamping, safe %, weighted agg, validation |
| PDF | `test_pdf_report.py` | PDF generation, empty subjects, scaling |
| RBAC | `test_rbac.py` | 7 roles, 60+ permissions, matrix generation |
| Workflow | `test_workflow.py` | 4 workflows, states, transitions, role validation |
| Curriculum | `test_curriculum.py` | 6 curricula, grading bands, gaps, points |
| Promotion | `test_promotion.py` | Logic, snapshots, graduation |
| **Integration** | | |
| Attendance | `test_attendance_workflow.py` | Record → verify stats, multi-status |
| Grading | `test_grading_workflow.py` | Weighted aggregation, all 25 boundaries |
| Promotion | `test_promotion_workflow.py` | Bulk promote, retain-by-mean, graduate, rollback |
| **E2E** | | |
| Smoke Test | `test_full_school_workflow.py` | 9-phase life cycle: onboarding → teaching → grading → promotion → audit |

Run: `pytest tests/ -v`

---

## Production Checklist

- [ ] Set `SECRET_KEY` via `openssl rand -hex 64`
- [ ] Configure `CORS_ORIGINS` to your frontend domain
- [ ] Enable HTTPS with NGINX reverse proxy
- [ ] Set up S3 credentials for file uploads
- [ ] Configure SMTP for password resets + notifications
- [ ] Set `DEBUG=false` and `ENVIRONMENT=production`
- [ ] Set up PostgreSQL daily backup cron job
- [ ] Configure monitoring (Prometheus, Grafana, Sentry)
- [ ] Run security audit: `python -m scripts.security_audit`
- [ ] Run benchmarks to tune pool size: `python -m benchmarks.bench_runner`

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12 + FastAPI (async) |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Cache / Queue | Redis + Celery |
| Frontend | React 18 + TypeScript + Tailwind CSS |
| State | Zustand |
| Charts | Recharts |
| PDF | ReportLab |
| Push | Firebase Cloud Messaging (FCM v1) |
| Mobile (future) | Flutter + Isar DB |

---

## Documentation

- `docs/api-reference.md` — Full curl examples for all 33 modules
- `docs/deployment-guide.md` — 10-step production deployment
- `docs/developer/guide.md` — Architecture, adding features, security, multi-tenancy

---

**Proprietary — All rights reserved.**
