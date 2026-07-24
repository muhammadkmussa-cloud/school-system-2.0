# School Management System — Complete System Specification

> **Version:** 1.0.0
> **Architecture:** Multi-tenant SaaS | Backend: Python/FastAPI/PostgreSQL | Frontend: React/TypeScript/Tailwind
> **Auth:** JWT (access + refresh) | **Password Hashing:** Argon2id | **Role Model:** RBAC (7 roles) + Subscription Tiers (4 levels)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture & Deployment](#2-architecture--deployment)
3. [Data Model (30 Tables)](#3-data-model)
4. [API Reference (130+ Endpoints)](#4-api-reference)
5. [Authentication & Authorization](#5-authentication--authorization)
6. [Role-Based Access Control](#6-role-based-access-control)
7. [Subscription Tiers & Billing](#7-subscription-tiers--billing)
8. [Account Lifecycle](#8-account-lifecycle)
9. [Multi-Tenant Isolation](#9-multi-tenant-isolation)
10. [School Onboarding Flow](#10-school-onboarding-flow)
11. [Teacher Provisioning & Management](#11-teacher-provisioning--management)
12. [Student Management](#12-student-management)
13. [Academic Structure](#13-academic-structure)
14. [Timetable Management](#14-timetable-management)
15. [Attendance System](#15-attendance-system)
16. [Gradebook & Assessments](#16-gradebook--assessments)
17. [Exams & Results](#17-exams--results)
18. [Lesson Planning](#18-lesson-planning)
19. [Curriculum Framework](#19-curriculum-framework)
20. [Assignments & Submissions](#20-assignments--submissions)
21. [Reports & Analytics](#21-reports--analytics)
22. [Calendar & Scheduling](#22-calendar--scheduling)
23. [Workflow Engine & Approvals](#23-workflow-engine--approvals)
24. [Audit Logging](#24-audit-logging)
25. [Import/Export](#25-importexport)
26. [Student Promotion](#26-student-promotion)
27. [Offline Sync](#27-offline-sync)
28. [Push Notifications](#28-push-notifications)
29. [Frontend Architecture](#29-frontend-architecture)
30. [Security & Compliance](#30-security--compliance)

---

## 1. System Overview

School Management System is a multi-tenant, teacher-centred school management platform designed for the African education context. It supports the full lifecycle of school administration — from onboarding a new school through to daily classroom operations, assessment, reporting, and analytics.

### Core Tenets

- **Multi-tenant by design** — every row is scoped to a `school_id`
- **Role-based access** — 7 roles from platform_admin to teacher
- **Tiered subscription** — Free / Starter / Professional / Enterprise
- **Offline-first capability** — sync engine for low-connectivity regions
- **Payment gateways** — M-Pesa (STK Push) + Paystack
- **African curriculum support** — KICD (Kenya), Nigerian, South African, international

### User Roles

| Role | Level | Scope | Description |
|------|-------|-------|-------------|
| Platform Admin | 100 | All schools | Superuser, manages all tenants, billing, platform settings |
| School Admin | 80 | Single school | Full school-level management: teachers, students, academics, settings |
| Deputy Principal | 70 | Single school | Assists admin, read access, student promotion/transfer |
| Head Teacher | 60 | Single school | Academic oversight, reports, exams management |
| Class Teacher | 40 | Assigned classes | Attendance + marks for assigned class |
| Subject Teacher | 30 | Assigned subjects | Marks + lessons for assigned subjects |
| Teacher | 20 | Self | Base teacher (view-only for assigned content) |

---

## 2. Architecture & Deployment

### Tech Stack

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React 18)                │
│  Vite + TypeScript + Tailwind CSS + Zustand + Axios │
├─────────────────────────────────────────────────────┤
│               API Gateway (FastAPI)                  │
│  JWT Auth | RBAC Enforcer | Rate Limiter | Audit     │
├─────────────────────────────────────────────────────┤
│                 Service Layer                         │
│  Auth | Teacher Provisioning | Staff Import | Billing│
│  Curriculum | Workflow | Notifications | Sync | Push │
├─────────────────────────────────────────────────────┤
│               Data Access (SQLAlchemy Async)          │
│  PostgreSQL 16 | Redis (cache/queue)                  │
├─────────────────────────────────────────────────────┤
│     External: S3 (uploads), SMTP (email),            │
│     M-Pesa API, Paystack API, Celery (background)    │
└─────────────────────────────────────────────────────┘
```

### Deployment Model

- **Docker Compose** for local development (API + DB + Redis)
- **Production**: Separate API workers (Gunicorn+Uvicorn), managed PostgreSQL, Redis Cluster
- **CI/CD**: GitHub Actions — lint, type-check, test, build, deploy

### Configuration

All settings via environment variables (`.env`):

| Category | Key Settings |
|----------|-------------|
| App | `APP_NAME`, `DEBUG`, `ENVIRONMENT`, `API_V1_PREFIX=/api/v1` |
| Server | `HOST=0.0.0.0`, `PORT=8000`, `WORKERS=4`, `CORS_ORIGINS` |
| Database | `DATABASE_URL` (postgresql+asyncpg), pool settings |
| JWT | `SECRET_KEY`, `JWT_ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=30` |
| Argon2 | Time cost 2, memory 19456KB, parallelism 1 |
| Limits | `MAX_TEACHERS_PER_SCHOOL=200`, `FAILED_LOGIN_LOCKOUT=5` |
| Storage | S3-compatible (MinIO, Cloudflare R2, AWS S3) |
| Email | SMTP with TLS |
| Payments | M-Pesa + Paystack timeouts, signature headers |

---

## 3. Data Model

The system has **30 database tables** across 17 model files, all inheriting from `TimestampMixin` (`id`, `created_at`, `updated_at`).

### Entity-Relationship Summary

```
School ──┬── User (school_admin, teacher, platform_admin)
         ├── Teacher
         ├── Student
         ├── AcademicYear ── Term
         ├── Class ── Stream
         ├── Subject ── Department
         ├── Timetable ── TimetableEntry
         ├── AttendanceRecord
         ├── Assessment ── Mark
         ├── LessonPlan
         ├── Assignment ── AssignmentSubmission
         ├── ExamSeries ── ExamPaper ── ExamScore
         ├── WorkflowDefinition ── WorkflowState ── WorkflowTransition
         ├── WorkflowInstance ── WorkflowAction
         ├── Curriculum ── CurriculumLevel ── GradingScheme ── GradeBand
         ├── SchoolCurriculum (junction)
         ├── SchoolSubscription ── Invoice ── Payment
         ├── AuditLog
         └── Notification
```

### Table Reference

#### `users` — All system users (platform/school/teacher)

| Column | Type | Constraints |
|--------|------|------------|
| id | UUID | PK |
| school_id | UUID | FK → schools, NOT NULL, indexed |
| username | String(100) | nullable, indexed |
| email | String(255) | UNIQUE, NOT NULL, indexed |
| hashed_password | String(255) | NOT NULL (Argon2id hash) |
| full_name | String(200) | NOT NULL |
| role | String(30) | NOT NULL, indexed |
| phone | String(30) | nullable |
| status | String(30) | `pending_first_login` / `active` / `locked` / `disabled`, indexed |
| must_change_password | Boolean | default true |
| terms_accepted | Boolean | default false |
| profile_completed | Boolean | default false |
| password_changed_at | DateTime(tz) | nullable |
| last_login_at | DateTime(tz) | nullable |
| failed_login_attempts | Integer | default 0 |
| locked_until | DateTime(tz) | nullable |
| refresh_token_jti | String(100) | nullable (for token revocation) |

#### `login_history` — Authentication attempts

| Column | Type | Constraints |
|--------|------|------------|
| id | UUID | PK |
| user_id | UUID | FK → users ON DELETE CASCADE |
| ip_address | String(45) | nullable |
| user_agent | Text | nullable |
| success | Boolean | NOT NULL |
| attempted_at | DateTime(tz) | server_default=now() |

#### `password_history` — Previous password hashes (prevents reuse)

| Column | Type | Constraints |
|--------|------|------------|
| id | UUID | PK |
| user_id | UUID | FK → users ON DELETE CASCADE, indexed |
| hashed_password | String(255) | NOT NULL |
| created_at | DateTime(tz) | server_default=now() |

#### `schools` — Tenant schools

| Column | Type | Constraints |
|--------|------|------------|
| name | String(200) | NOT NULL |
| code | String(20) | UNIQUE, NOT NULL, indexed |
| email | String(255) | nullable |
| phone | String(30) | nullable |
| address | Text | nullable |
| logo_url | String(500) | nullable |
| is_active | Boolean | default true |
| subscription_tier | String(50) | default `free` |
| subscription_expires_at | String(50) | nullable |

Relationships: users, teachers, students, academic_years, classes, streams, subjects, departments, timetables, assessments, lesson_plans

#### `teachers` — Teacher profiles (1:1 with users)

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| user_id | UUID | FK → users ON DELETE CASCADE, UNIQUE |
| employee_number | String(50) | UNIQUE, NOT NULL, indexed |
| full_name | String(200) | NOT NULL |
| email | String(255) | NOT NULL |
| phone | String(30) | nullable |
| is_active | Boolean | default true |

#### `students` — Student records

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| admission_number | String(50) | NOT NULL, indexed |
| full_name | String(200) | NOT NULL |
| gender | String(10) | NOT NULL (male/female/other) |
| date_of_birth | Date | NOT NULL |
| class_id | UUID | FK → classes ON DELETE SET NULL |
| stream_id | UUID | FK → streams ON DELETE SET NULL, nullable |
| academic_year_id | UUID | FK → academic_years ON DELETE CASCADE |
| parent_name/phone/email | Various | nullable |
| medical_notes | Text | nullable |
| status | String(20) | default `active` (active/archived/transferred/graduated) |

**Unique constraint:** `(school_id, admission_number)`

#### `academic_years` — School years

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| name | String(100) | NOT NULL (e.g. "2026 Academic Year") |
| start_date / end_date | Date | NOT NULL |
| is_current | Boolean | default false |

#### `terms` — Academic terms within a year

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| academic_year_id | UUID | FK → academic_years ON DELETE CASCADE |
| name | String(100) | NOT NULL |
| term_number | Integer | NOT NULL (1/2/3) |
| start_date / end_date | Date | NOT NULL |
| is_current | Boolean | default false |

#### `classes` — Form/grade levels

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| name | String(100) | NOT NULL (e.g. "Form 1", "Grade 4") |
| level | Integer | nullable (1-4 for secondary) |
| description | String(500) | nullable |

#### `streams` — Divisions within a class

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| class_id | UUID | FK → classes ON DELETE CASCADE |
| name | String(100) | NOT NULL (e.g. "East", "West", "North", "South") |

#### `subjects` — Academic subjects

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| department_id | UUID | FK → departments ON DELETE SET NULL, nullable |
| code | String(20) | NOT NULL (e.g. "MAT", "ENG") |
| name | String(200) | NOT NULL |
| description | String(500) | nullable |

#### `departments` — Subject groupings

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| name | String(200) | NOT NULL |
| description | String(500) | nullable |

#### `timetables` — Timetable definitions

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| academic_year_id | UUID | FK → academic_years ON DELETE CASCADE |
| name | String(200) | NOT NULL |
| is_active | Boolean | default true |

#### `timetable_entries` — Individual class slots

| Column | Type | Constraints |
|--------|------|------------|
| timetable_id | UUID | FK → timetables ON DELETE CASCADE |
| day_of_week | Integer | 0=Mon..6=Sun |
| start_time / end_time | Time | NOT NULL |
| subject_id | UUID | FK → subjects ON DELETE CASCADE |
| teacher_id | UUID | FK → teachers ON DELETE CASCADE |
| class_id | UUID | FK → classes ON DELETE CASCADE |
| room | String(100) | nullable |

#### `attendance_records` — Daily attendance

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| student_id | UUID | FK → students ON DELETE CASCADE, indexed |
| class_id | UUID | FK → classes ON DELETE SET NULL, indexed |
| recorded_by | UUID | FK → users ON DELETE SET NULL |
| attendance_date | Date | NOT NULL, indexed |
| status | String(20) | present / absent / late / excused |
| remarks | String(500) | nullable |
| synced | Boolean | default true |

**Unique constraint on:** `(student_id, attendance_date)`

#### `assessments` — Tests/exams/quizzes

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| subject_id | UUID | FK → subjects, indexed |
| teacher_id | UUID | FK → teachers ON DELETE SET NULL |
| class_id | UUID | FK → classes, indexed |
| term_id | UUID | FK → terms, nullable |
| name | String(200) | NOT NULL |
| assessment_type | String(50) | exam / test / quiz / assignment / project |
| max_score | Float | NOT NULL |
| weight | Float | default 1.0 |
| date_administered | Date | nullable |
| description | Text | nullable |

#### `marks` — Student scores per assessment

| Column | Type | Constraints |
|--------|------|------------|
| assessment_id | UUID | FK → assessments ON DELETE CASCADE |
| student_id | UUID | FK → students ON DELETE CASCADE |
| score | Float | NOT NULL |
| grade | String(5) | nullable (auto-calculated from curriculum) |
| remarks | String(500) | nullable |
| synced | Boolean | default true |

#### `curricula` — Curriculum frameworks (KICD, Nigerian, etc.)

| Column | Type | Constraints |
|--------|------|------------|
| name | String(200) | UNIQUE |
| code | String(20) | UNIQUE, NOT NULL |
| description | Text | nullable |
| country | String(100) | nullable |
| is_active | Boolean | default true |
| metadata | JSON | nullable |

#### `curriculum_levels` — Grade levels in a curriculum

| Column | Type | Constraints |
|--------|------|------------|
| curriculum_id | UUID | FK → curricula ON DELETE CASCADE |
| name | String(100) | NOT NULL |
| code | String(20) | NOT NULL |
| sort_order | Integer | NOT NULL |
| is_terminal | Boolean | default false |
| promotion_to_level_id | UUID | nullable |

**Unique:** `(curriculum_id, code)`

#### `grading_schemes` — Grading systems

| Column | Type | Constraints |
|--------|------|------------|
| curriculum_id | UUID | FK → curricula ON DELETE CASCADE |
| name | String(100) | NOT NULL |
| is_default | Boolean | default false |

#### `grade_bands` — Letter grade definitions

| Column | Type | Constraints |
|--------|------|------------|
| scheme_id | UUID | FK → grading_schemes ON DELETE CASCADE |
| letter | String(5) | NOT NULL (A/B/C/D/E) |
| min_percentage / max_percentage | Float | NOT NULL |
| points | Integer | default 1 |
| remark | String(200) | nullable |

#### `exam_series` — Exam periods (CATs, Midterms, End Terms)

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| term_id | UUID | FK → terms ON DELETE CASCADE |
| name | String(200) | NOT NULL |
| series_type | String(30) | CAT / Midterm / End Term / Practical / Project / Mock |
| start_date / end_date | Date | NOT NULL |
| is_published | Boolean | default false |
| weight_percentage | Float | default 30.0 |

#### `exam_papers` — Individual exam papers

| Column | Type | Constraints |
|--------|------|------------|
| series_id | UUID | FK → exam_series ON DELETE CASCADE |
| subject_id | UUID | FK → subjects, NOT NULL |
| class_id | UUID | FK → classes, NOT NULL |
| name | String(200) | NOT NULL |
| paper_code | String(20) | nullable |
| max_score | Float | NOT NULL |
| weight | Float | default 1.0 |
| duration_minutes | Integer | nullable |
| exam_date | Date | nullable |

#### `exam_scores` — Student scores per exam paper

| Column | Type | Constraints |
|--------|------|------------|
| paper_id | UUID | FK → exam_papers ON DELETE CASCADE |
| student_id | UUID | FK → students ON DELETE CASCADE |
| score | Float | NOT NULL |
| grade | String(5) | nullable |
| is_absent | Boolean | default false |
| remarks | String(500) | nullable |

#### `lesson_plans` — Teacher lesson plans

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| teacher_id | UUID | FK → teachers ON DELETE SET NULL |
| subject_id | UUID | FK → subjects ON DELETE CASCADE |
| class_id | UUID | FK → classes ON DELETE CASCADE |
| topic | String(300) | NOT NULL |
| objectives / activities / resources / assessment / homework | Text | nullable |
| completion_status | String(30) | planned / in_progress / completed |
| week_number / term_number | Integer | nullable |
| source_plan_id | UUID | nullable (for duplication tracking) |

#### `assignments` — Digital assignments

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| teacher_id | UUID | FK → teachers ON DELETE SET NULL |
| subject_id | UUID | FK → subjects ON DELETE CASCADE |
| class_id | UUID | FK → classes ON DELETE CASCADE |
| title | String(300) | NOT NULL |
| description | Text | nullable |
| assignment_type | String(30) | default `homework` |
| due_date | DateTime(tz) | NOT NULL |
| max_score | Float | nullable |
| is_published | Boolean | default true |
| allow_late_submission | Boolean | default true |

#### `assignment_submissions` — Student submissions

| Column | Type | Constraints |
|--------|------|------------|
| assignment_id | UUID | FK → assignments ON DELETE CASCADE |
| student_id | UUID | FK → students ON DELETE CASCADE |
| submitted_at | DateTime(tz) | nullable |
| is_late | Boolean | default false |
| content / attachment_url | Text/String(500) | nullable |
| score / grade | Float / String(5) | nullable |
| teacher_comment | Text | nullable |
| graded_at | DateTime(tz) | nullable |
| graded_by | UUID | FK → users ON DELETE SET NULL |

#### `workflow_definitions` — Approval workflow templates

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| name | String(200) | NOT NULL |
| entity_type | String(50) | NOT NULL |
| description | Text | nullable |
| is_active | Boolean | default true |
| config | JSON | nullable |

#### `workflow_states` — Workflow states

| Column | Type | Constraints |
|--------|------|------------|
| workflow_id | UUID | FK → workflow_definitions ON DELETE CASCADE |
| name | String(100) | NOT NULL |
| display_name | String(200) | NOT NULL |
| sort_order | Integer | NOT NULL |
| required_role | String(50) | NOT NULL |
| is_final | Boolean | default false |
| color | String(20) | nullable |

#### `workflow_transitions` — State transitions

| Column | Type | Constraints |
|--------|------|------------|
| from_state_id | UUID | FK → workflow_states ON DELETE CASCADE |
| to_state_id | UUID | FK → workflow_states ON DELETE CASCADE |
| action_name | String(100) | NOT NULL |
| display_name | String(200) | NOT NULL |

#### `workflow_instances` — Running workflow instances

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools, indexed |
| workflow_id | UUID | FK → workflow_definitions |
| entity_id | String(100) | NOT NULL (polymorphic reference) |
| current_state | String(100) | NOT NULL |
| payload | JSON | nullable |
| completed_at | DateTime(tz) | nullable |

#### `workflow_actions` — Action history on workflow instances

| Column | Type | Constraints |
|--------|------|------------|
| instance_id | UUID | FK → workflow_instances ON DELETE CASCADE |
| actor_id | UUID | FK → users ON DELETE SET NULL |
| from_state / to_state | String(100) | NOT NULL |
| action | String(100) | NOT NULL |
| comment / metadata | Text / JSON | nullable |

#### `school_subscriptions` — Billing subscriptions

| Column | Type | Constraints |
|--------|------|------------|
| school_id | UUID | FK → schools ON DELETE CASCADE, UNIQUE |
| tier | String(30) | default `free` |
| status | String(20) | active / past_due / cancelled / trialing |
| billing_cycle | String(10) | monthly / yearly |
| trial_ends_at | DateTime(tz) | nullable |
| payment_method | String(20) | mpesa / paystack / none |
| auto_renew | Boolean | default true |
| mpesa_phone / paystack_email / paystack_customer_code | Various | nullable |
| extra_features | JSONB | default [] |

#### `invoices` — Billing invoices

| Column | Type | Constraints |
|--------|------|------------|
| subscription_id | UUID | FK → school_subscriptions |
| school_id | UUID | FK → schools, indexed |
| invoice_number | String(30) | UNIQUE, NOT NULL |
| amount_kes / amount_paid_kes | Float | NOT NULL / default 0 |
| status | String(20) | pending / paid / overdue / cancelled |
| due_date | DateTime(tz) | NOT NULL |
| paid_at | DateTime(tz) | nullable |
| period_start / period_end | DateTime(tz) | NOT NULL |

#### `payments` — Payment transactions

| Column | Type | Constraints |
|--------|------|------------|
| invoice_id | UUID | FK → invoices ON DELETE CASCADE |
| school_id | UUID | FK → schools, indexed |
| amount_kes | Float | NOT NULL |
| gateway | String(20) | mpesa / paystack |
| gateway_reference | String(100) | nullable, indexed |
| mpesa_phone / mpesa_receipt | Various | nullable |
| paystack_authorization_code / card_type / last4 | Various | nullable |
| status | String(20) | pending / success / failed |

#### `audit_logs` — Immutable audit trail

| Column | Type | Constraints |
|--------|------|------------|
| id | UUID | PK |
| school_id | UUID | FK → schools ON DELETE CASCADE, indexed |
| actor_id | UUID | FK → users ON DELETE SET NULL, indexed |
| actor_role / actor_name | Various | nullable |
| action | String(50) | NOT NULL, indexed |
| entity_type | String(50) | NOT NULL, indexed |
| entity_id | String(100) | nullable, indexed |
| changes | JSON | nullable |
| summary | Text | nullable |
| ip_address / endpoint / user_agent / request_id | Various | nullable |
| created_at | DateTime(tz) | server_default=now(), indexed |

---

## 4. API Reference

All endpoints are prefixed with `/api/v1`.

### Authentication (`/auth`)

| Method | Endpoint | Auth | Request | Response |
|--------|----------|------|---------|----------|
| POST | `/login` | Public | `{school_code, username, password}` | `{access_token, refresh_token, token_type, expires_in, user}` |
| POST | `/refresh` | Public | `{refresh_token}` | `{access_token, refresh_token, token_type, expires_in, user}` |
| POST | `/first-login` | CurrentUser | `{new_password, email?, phone?, accept_terms}` | `TokenResponse` |
| POST | `/change-password` | CurrentUser | `{current_password, new_password}` | 204 |
| POST | `/logout` | CurrentUser | — | 204 |
| GET | `/me` | CurrentUser | — | `UserOut` |

### Users (`/users`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | SchoolAdmin | List users (paginated, searchable, filter by role) |
| POST | `/` | SchoolAdmin | Create user |
| GET | `/{user_id}` | SchoolAdmin | Get user |
| PATCH | `/{user_id}` | SchoolAdmin | Update user |
| POST | `/{user_id}/reset-password` | SchoolAdmin | Reset user password (204) |

### Schools (`/schools`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | PlatformAdmin | List schools (paginated, searchable) |
| POST | `/` | PlatformAdmin | Create school |
| GET | `/{school_id}` | PlatformAdmin | Get school |
| PATCH | `/{school_id}` | PlatformAdmin | Update school |
| POST | `/{school_id}/toggle-active` | PlatformAdmin | Activate/suspend school |

### Students (`/students`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | Staff | List (paginated, searchable, filter by class/status) |
| POST | `/` | SchoolAdmin | Create student |
| GET | `/{student_id}` | Staff | Get student |
| PATCH | `/{student_id}` | SchoolAdmin | Update student |
| POST | `/{student_id}/transfer` | SchoolAdmin | Transfer to new class/stream |
| POST | `/{student_id}/promote` | SchoolAdmin | Promote to next class |
| POST | `/{student_id}/archive` | SchoolAdmin | Archive student |

### Teachers (`/teachers`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | SchoolAdmin | List (paginated, searchable, includes user_status/must_change_password) |
| POST | `/` | SchoolAdmin | Create teacher (auto-generates username + temp password) |
| POST | `/bulk` | SchoolAdmin | Bulk generate N accounts |
| GET | `/credentials` | SchoolAdmin | List all teacher credentials |
| GET | `/{teacher_id}` | SchoolAdmin | Get teacher |
| PATCH | `/{teacher_id}` | SchoolAdmin | Update teacher |
| POST | `/{teacher_id}/toggle-active` | SchoolAdmin | Toggle active state |
| POST | `/{teacher_id}/reset-password` | SchoolAdmin | Reset password |
| POST | `/{teacher_id}/lock` | SchoolAdmin | Lock account (status=locked, 1hr auto-expiry) |
| POST | `/{teacher_id}/unlock` | SchoolAdmin | Unlock account (clears lockout) |
| POST | `/{teacher_id}/force-reset` | SchoolAdmin | Force password reset (returns new temp password) |
| GET | `/{teacher_id}/account-status` | SchoolAdmin | Full status: user info, recent login attempts, password history |

### Academic (`/academic`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/years` | Staff | List academic years |
| POST | `/years` | SchoolAdmin | Create year |
| PATCH | `/years/{year_id}` | SchoolAdmin | Update year |
| GET | `/terms` | Staff | List terms (filter by academic_year_id) |
| POST | `/terms` | SchoolAdmin | Create term |
| GET | `/classes` | Staff | List classes |
| POST | `/classes` | SchoolAdmin | Create class |
| GET | `/streams` | Staff | List streams (filter by class_id) |
| POST | `/streams` | SchoolAdmin | Create stream |
| GET | `/subjects` | Staff | List subjects |
| POST | `/subjects` | SchoolAdmin | Create subject |
| GET | `/departments` | Staff | List departments |
| POST | `/departments` | SchoolAdmin | Create department |

### Timetable (`/timetable`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | Staff | List timetables |
| POST | `/` | SchoolAdmin | Create timetable with entries |
| GET | `/{timetable_id}` | Staff | Get timetable |
| POST | `/{timetable_id}/entries` | SchoolAdmin | Add entry |
| DELETE | `/{timetable_id}/entries/{entry_id}` | SchoolAdmin | Remove entry |
| GET | `/my` | Staff | Get current user's timetable (teacher) |
| POST | `/check-conflicts` | SchoolAdmin | Check scheduling conflicts |

### Attendance (`/attendance`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/batch` | Staff | Record attendance for multiple students |
| GET | `/class/{class_id}` | Staff | Get attendance for class on date |
| GET | `/student/{student_id}` | Staff | Get student attendance history |
| GET | `/stats` | Staff | Attendance statistics |

### Gradebook (`/gradebook`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/assessments` | Staff | List assessments (filter by class/subject/term) |
| POST | `/assessments` | Staff | Create assessment |
| GET | `/assessments/{id}` | Staff | Get assessment |
| POST | `/assessments/{id}/marks` | Staff | Record marks |
| GET | `/assessments/{id}/marks` | Staff | Get marks |
| GET | `/assessments/{id}/stats` | Staff | Assessment statistics (avg, highest, lowest, grade distribution) |
| GET | `/student/{student_id}/grades` | Staff | Student grade summary |

### Exams (`/exams`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/series` | Staff | List exam series |
| POST | `/series` | ExamsManage | Create series |
| POST | `/papers` | ExamsManage | Create exam paper |
| GET | `/papers/{series_id}` | Staff | List papers in series |
| POST | `/papers/{paper_id}/scores` | Staff | Record exam scores |
| GET | `/results/student/{student_id}` | Staff | Student exam result |
| GET | `/results/class/{class_id}/ranking` | Staff | Class ranking with mean grades |

### Lessons (`/lessons`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | Staff | List (paginated, filter by class/subject/status) |
| POST | `/` | Staff | Create lesson plan |
| POST | `/duplicate` | Staff | Duplicate lesson plan |
| GET | `/{lesson_id}` | Staff | Get lesson |
| PATCH | `/{lesson_id}` | Staff | Update lesson |
| POST | `/{lesson_id}/complete` | Staff | Mark lesson complete |

### Reports (`/reports`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/attendance` | Staff | Attendance report (JSON or CSV) |
| GET | `/students` | Staff | Student list (JSON or CSV) |
| GET | `/teacher-workload` | SchoolAdmin | Teacher workload report |
| GET | `/subject-performance` | SchoolAdmin | Subject performance analysis |

### Results (`/results`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/student/{id}/report-card` | Staff | Full report card |
| GET | `/student/{id}/report-card/pdf` | Staff | PDF report card download |
| GET | `/class/{id}/summary` | Staff | Aggregated class summary |
| GET | `/class/{id}/rankings` | Staff | Class rankings |

### Analytics (`/analytics`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/overview` | Staff | School health snapshot |
| GET | `/attendance-trend` | Staff | Daily attendance % over N days |
| GET | `/gender-analysis` | Staff | Male vs female analysis |
| GET | `/syllabus-coverage` | Staff | Curriculum coverage |
| GET | `/teacher-effectiveness` | Staff | Teacher rankings |

### Advanced Dashboard (`/dashboard/advanced`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/executive-summary` | Staff | KPI snapshot |
| GET | `/performance-heatmap` | SchoolAdmin | Subject×Class performance matrix |
| GET | `/at-risk-students` | SchoolAdmin | Students below threshold |
| GET | `/term-comparison` | SchoolAdmin | Term-over-term comparison |
| GET | `/stream-comparison` | SchoolAdmin | Stream performance comparison |
| GET | `/teacher-leaderboard` | SchoolAdmin | Teacher ranking by composite score |

### Dashboard (`/dashboard`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/admin` | Staff | Admin KPIs (totals, attendance %, recent assessments) |
| GET | `/teacher` | Staff | Teacher dashboard (today's timetable, pending attendance) |

### Curriculum (`/curriculum`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | CurrentUser | List available curricula |
| GET | `/{curriculum_id}` | CurrentUser | Get curriculum with levels + grading |
| POST | `/assign` | SchoolAdmin | Assign curriculum to school |
| GET | `/my/levels` | CurrentUser | School's curriculum levels |
| GET | `/my/grade` | CurrentUser | Resolve grade from percentage |

### Workflow (`/workflow`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/definitions` | Staff | List workflow definitions |
| GET | `/definitions/{workflow_id}` | Staff | Get workflow with states |
| POST | `/instances/{id}/transition` | Staff | Execute a state transition |
| GET | `/instances/{id}/actions` | Staff | Available actions |
| GET | `/instances/{id}/history` | Staff | Action history |

### Audit (`/audit`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | SchoolAdmin | Filtered audit log (entity_type, action, actor, date range, paginated) |
| GET | `/entity/{entity_type}/{entity_id}` | SchoolAdmin | Entity-specific audit trail |

### Onboarding (`/onboarding`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/setup/step-1` | SchoolAdmin | School Info (name, code, type, curriculum, country, address, contact, timezone, academic year) |
| POST | `/setup/step-2` | SchoolAdmin | Academic Structure (grades, streams, subjects, terms, grading) |
| POST | `/setup/step-3/manual` | SchoolAdmin | Manual staff provisioning |
| POST | `/setup/step-3/validate` | SchoolAdmin | Validate CSV/Excel file |
| POST | `/setup/step-3/confirm` | SchoolAdmin | Confirm staff import |
| GET | `/setup/staff-template` | Public | Download staff import CSV template |
| GET | `/setup/status` | SchoolAdmin | Check setup progress |

### Billing (`/billing`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/tiers` | Public | List pricing tiers |
| GET | `/subscription` | SchoolAdmin | Current subscription + trial |
| GET | `/subscription/trial-status` | SchoolAdmin | Trial status and read-only flags |
| POST | `/subscription/change` | SchoolAdmin | Change tier |
| GET | `/subscription/check-feature` | SchoolAdmin | Check feature access |
| POST | `/mpesa/pay` | SchoolAdmin | Initiate M-Pesa STK Push |
| POST | `/mpesa/callback` | Public | M-Pesa payment callback |
| POST | `/mpesa/query` | SchoolAdmin | Query M-Pesa payment status |
| POST | `/paystack/pay` | SchoolAdmin | Initiate Paystack checkout |
| GET | `/paystack/verify` | SchoolAdmin | Verify Paystack payment |
| POST | `/paystack/webhook` | Public | Paystack webhook |

### Imports (`/imports`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/students/csv` | StudentImport | CSV import students |
| POST | `/teachers/csv` | StudentImport | CSV import teachers |
| POST | `/marks/csv` | StudentImport | CSV import marks (requires assessment_id) |
| GET | `/templates/students` | Public | Download student CSV template |
| GET | `/templates/teachers` | Public | Download teacher CSV template |

### Promotion (`/promotion`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/class/{class_id}` | StudentPromote | Promote class to next level |
| POST | `/rollback` | StudentPromote | Undo last promotion |
| GET | `/path/{class_id}` | StudentPromote | View promotion chain |

### Assignments (`/assignments`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | Staff | List assignments (paginated, filter by class) |
| POST | `/` | Staff | Create assignment |
| GET | `/{id}/submissions` | Staff | List submissions |
| POST | `/submissions/{id}/grade` | Staff | Grade submission |

### Calendar (`/calendar`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/my` | Staff | User's weekly calendar |
| GET | `/school` | Staff | School events |
| GET | `/my.ics` | Staff | ICS subscription link |
| GET | `/upcoming` | Staff | Upcoming events (next N days) |

### Notifications (`/notifications`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/` | CurrentUser | List notifications |
| POST | `/{id}/read` | CurrentUser | Mark as read |
| POST | `/read-all` | CurrentUser | Mark all read |
| GET | `/unread-count` | CurrentUser | Unread count |
| POST | `/send` | CurrentUser | Send notification |

### Sync (`/sync`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/push` | CurrentUser | Push offline changes |
| GET | `/status` | CurrentUser | Pending sync counts |

### Platform Admin (`/platform`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/dashboard` | PlatformAdmin | SaaS-level metrics (total schools, students, teachers, audit events, top schools) |
| GET | `/schools/stats` | PlatformAdmin | Per-school statistics |
| GET | `/users/summary` | PlatformAdmin | User distribution by role |

### Push (`/push`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/register` | CurrentUser | Register device token |
| POST | `/unregister` | CurrentUser | Unregister device |
| GET | `/status` | CurrentUser | Device count |
| POST | `/send` | CurrentUser | Send push notification |

### Health (`/health/full`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/health/full` | None | System health check (status, version, uptime, DB check) |

---

## 5. Authentication & Authorization

### Login Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User     │────▶│ /auth/   │────▶│  Verify  │────▶│  Issue   │
│  submits  │     │  login   │     │  school  │     │  tokens  │
│  school+  │     │          │     │  code +  │     │          │
│  username │     │          │     │  creds   │     │          │
│  + pw     │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Check status │
                                 │  pending?     │──▶ must_change_password=true
                                 │  locked?      │──▶ "Account locked" error
                                 │  disabled?    │──▶ "Account disabled" error
                                 │  active?      │──▶ proceed
                                 └──────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Validate pw   │
                                 │  (verify_     │──▶ Fail: increment attempts
                                 │  password)     │     Lock if > FAILED_LOGIN_LOCKOUT
                                 └──────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Record login  │
                                 │  history,      │
                                 │  issue access  │
                                 │  + refresh JWT │
                                 └──────────────┘
```

### Token System

- **Access Token**: Short-lived (30 min), JWT with `sub` (user_id), `type=access`, `school_id`
- **Refresh Token**: Long-lived (30 days), JWT with `sub`, `type=refresh`, `jti` (unique ID for revocation)
- **Rotation**: Each refresh invalidates the previous refresh token by generating a new `jti`
- **Revocation**: On logout, `refresh_token_jti` is set to null

### Multi-Tenant Authentication

1. User enters **school code** + **username** + **password**
2. System looks up school by code
3. System looks up user by username within that school
4. Validates password via `verify_password(plain, hashed)` (Argon2id)
5. Checks account status:
   - `pending_first_login` → login succeeds but forces first-login wizard
   - `locked` → rejects with "Account locked. Try again later."
   - `disabled` → rejects with "Account disabled. Contact administrator."
   - `active` → normal login
6. Records login attempt in `login_history`
7. On 5 consecutive failures → auto-locks account for 15 minutes
8. Issues JWT pair with school_id embedded

### First-Login Flow

When `must_change_password=True`:
1. User logs in with temp credentials
2. Frontend redirects to `/first-login`
3. 3-Step wizard:
   - **Step 1**: Set new password (validated: min 8 chars, not in last 5 passwords)
   - **Step 2**: Confirm email + phone
   - **Step 3**: Accept Terms of Service
4. POST `/auth/first-login` → hashes password, adds to `password_history`, sets `must_change_password=False`, `terms_accepted=True`, `profile_completed=True`, `status=active`
5. Issues new access/refresh tokens

### Password Security

- **Hashing**: Argon2id (configurable time/memory/parallelism)
- **History**: Last 5 hashes stored in `password_history` — prevents reuse
- **Change**: `/auth/change-password` requires current password verification
- **Admin Reset**: `/teachers/{id}/force-reset` generates new temp password, sets `must_change_password=True`, clears all active sessions

---

## 6. Role-Based Access Control

### Role Hierarchy & Permissions

```
platform_admin  ── *:* (god-mode)
school_admin    ── full CRUD for school (students, teachers, academic, settings, users)
deputy_principal ── read, promote, transfer students; read teachers; reports
head_teacher    ── academic oversight, exams, reports, timetable
class_teacher   ── attendance + marks for assigned class
subject_teacher ── marks + lessons for assigned subjects
teacher         ── basic attendance, marks, lessons
```

### Permission Model

Two-layer enforcement:
1. **Route-level** (`rbac_enforcer.py`): Maps `METHOD /path` → `permission: string`
2. **Role-level** (`rbac.py`): Maps role → `set[permission]`

Check: `has_permission(role, permission)` resolves wildcards (`*:* `, `resource:*`)

### RBAC Route Map (100+ entries)

Every route is registered with its required permission. Example entries:
- `POST /teachers` → `teachers:create`
- `POST /teachers/{id}/lock` → `teachers:manage`
- `POST /attendance/batch` → `attendance:write`
- `GET /reports/attendance` → `reports:view`

### Effective Permissions Graph

Permissions are the union of:
- **Role-based permissions** (from RBAC)
- **Subscription tier gating** (from subscriptions → `TIER_FEATURE_TO_PERMISSION`)

A feature is available only if the **user's role** AND **school's subscription tier** both grant it.

---

## 7. Subscription Tiers & Billing

### Tiers

| Tier | Monthly | Yearly | Max Students | Max Teachers | Key Features |
|------|---------|--------|-------------|-------------|-------------|
| **Free** | KES 0 | KES 0 | 0 | 1 | Personal timetable, lesson planner |
| **Starter** | KES 2,500 | KES 25,000 | 200 | 10 | Attendance, marks, report cards, timetable management |
| **Professional** | KES 7,500 | KES 75,000 | 1,000 | 50 | Analytics, workflows, imports, audit, assignments, exams |
| **Enterprise** | KES 25,000 | KES 250,000 | 10,000 | 500 | API access, custom branding, priority support, multi-campus |

### Billing Flow

```
School Admin clicks "Upgrade"
         │
         ▼
Select tier + billing cycle (monthly/yearly)
         │
         ▼
Select payment method:
  ┌──────┴──────┐
  │             │
  ▼             ▼
M-Pesa        Paystack
(STK Push)    (Checkout)
  │             │
  ▼             ▼
Enter phone   Redirect to
number        Paystack URL
  │             │
  ▼             ▼
M-Pesa API    Paystack API
  │             │
  ▼             ▼
Callback/     Webhook/
Poll          Redirect
  │             │
  └──────┬──────┘
         ▼
  Invoice created,
  subscription
  activated/upgraded
```

### Payment Gateways

- **M-Pesa**: STK Push via Safaricom API - sends payment request to customer's phone
- **Paystack**: Redirect to Paystack checkout, webhook verification

### Feature Gating

Each subscription tier defines a set of `features` (e.g., `students_create`, `timetable_manage`). These map to permissions via `TIER_FEATURE_TO_PERMISSION`. Before executing any operation, both RBAC role check AND subscription feature check must pass.

### Trial Lifecycle

- New schools get a trial period (configurable)
- During trial: read-only mode after expiration
- Warning notifications sent before trial ends
- Trial status endpoint returns `is_read_only`, `days_left`, `action_required`

---

## 8. Account Lifecycle

### States

```
                  ┌──────────────────┐
                  │  Pending First   │
                  │     Login        │
                  └────────┬─────────┘
                           │ first-login completed
                           ▼
                  ┌──────────────────┐
           ┌─────│     Active       │──────┐
           │     └────────┬─────────┘      │
           │              │                │
       5 failed       admin lock       admin disable
        logins          │                │
           │              │                │
           ▼              ▼                ▼
   ┌────────────┐ ┌────────────┐ ┌──────────────┐
   │   Locked   │ │   Locked   │ │   Disabled   │
   │ (auto 15m) │ │ (admin)    │ │              │
   └────────────┘ └────────────┘ └──────────────┘
        │              │
    auto-expire     admin unlock
        │              │
        └──────┬───────┘
               ▼
          ┌────────┐
          │ Active │
          └────────┘
```

### Lifecycle Events (audited)

| Event | Trigger | Action |
|-------|---------|--------|
| `teacher_created` | Teacher account created | Logs actor, target |
| `temp_password_generated` | Bulk provision / admin reset | Logs event |
| `first_login_completed` | User completes first-login wizard | Sets status=active |
| `password_changed` | User changes password | Adds to password_history |
| `password_reset_by_admin` | Admin force-resets password | Clears sessions, sets must_change_password |
| `account_locked` | 5 failed logins or admin lock | Sets status=locked, locked_until |
| `account_unlocked` | Admin unlocks or auto-expiry | Clears locked_until, reset attempts |
| `account_disabled` | Admin toggles active off | Sets status=disabled |
| `account_enabled` | Admin toggles active on | Sets status=active |
| `failed_login` | Failed authentication | Records in login_history |

---

## 9. Multi-Tenant Isolation

### Schema-Level

Every tenant-scoped table has a `school_id` column with a foreign key to `schools.id ON DELETE CASCADE`. This means:

- When a school is deleted, ALL its data is automatically cleaned
- All queries filter by `current_user.school_id`
- Platform admins can see all schools' data (role-based)

### Enforcement Points

1. **Database layer**: `school_id` FK with CASCADE delete
2. **API layer**: `RequireSchoolAdmin` dependency checks school_id match
3. **Service layer**: All CRUD operations filter by school_id
4. **RBAC enforcer**: `_validate_school_scope` checks student/class belongs to user's school
5. **JWT**: School_id is NOT embedded in the token; it's looked up from the user record on every request

### Platform Admin Access

Platform admins bypass school-scoping and see all tenants. The `/platform/*` endpoints provide SaaS-level aggregated views.

---

## 10. School Onboarding Flow

### 3-Step Setup Wizard

```
Step 1: School Information
├── School name, code (unique), type (primary/secondary/mixed)
├── Curriculum selection (KICD, Nigerian, etc.)
├── Country, county, address
├── Contact email, phone
├── Timezone
└── Academic year (name, start, end)

Step 2: Academic Structure
├── Grades/Forms (name, level, number of streams)
├── Stream names (auto-generated or custom)
├── Subjects (code, name, elective flag, department)
├── Term names (3 terms default)
└── Grading system (A-F, numeric, custom)

Step 3: Staff Setup
├── Mode: Manual entry or Bulk import
├── Manual: Dynamic rows (name, email, phone, employee number)
├── Bulk: CSV/Excel upload
│   ├── Validate file → preview + errors
│   └── Confirm → creates accounts
└── Result: Credential display with print/CSV export
```

### What Gets Created

On completing all 3 steps:
- School record
- School admin user
- Academic year + 3 terms
- Classes + streams
- Subjects + departments
- Teacher accounts (each with User + Teacher record)
- Default workflow definitions

---

## 11. Teacher Provisioning & Management

### Account Creation

Teachers can only be created by school admins — NO self-registration.

**Username generation**: `teacher.{employee_number_lower}` (e.g. `teacher.tch0001`)

**Default account state**:
- `status = "pending_first_login"`
- `must_change_password = True`
- `role = "teacher"`
- `school_id` auto-inherited from admin
- Temp password auto-generated (`uuid4().hex[:12]`)

### Creation Methods

1. **Single create**: `POST /teachers` with form data
2. **Bulk generate**: `POST /teachers/bulk` with count → generates N sequential accounts
3. **Bulk import**: CSV/Excel upload via `/onboarding/setup/step-3/validate` + `/confirm`

### Account Management

| Action | Method | Endpoint |
|--------|--------|----------|
| List | GET | `/teachers` |
| View | GET | `/{id}` |
| Update | PATCH | `/{id}` |
| Toggle active | POST | `/{id}/toggle-active` |
| Reset password | POST | `/{id}/reset-password` |
| Lock | POST | `/{id}/lock` |
| Unlock | POST | `/{id}/unlock` |
| Force reset | POST | `/{id}/force-reset` |
| Account status | GET | `/{id}/account-status` |
| Credentials | GET | `/credentials` |
| Reset passwords (batch) | Admin selects multiple → batch action |

### Credential Export

After creation, admin can:
- **Print**: Styled HTML with all temp passwords
- **CSV**: Download credentials file
- **Copy individual**: One-click copy per password

---

## 12. Student Management

### CRUD Operations

- **Create**: School admin enters admission number, name, gender, DOB, class, stream, academic year, parent info
- **Read**: Paginated, searchable, filterable by class/status
- **Update**: Edit any field
- **Archive**: Soft-delete (status = archived)
- **Transfer**: Move to different class/stream
- **Promote**: Move to next grade level

### Fields

- Admission number (unique per school)
- Full name
- Gender (male/female/other)
- Date of birth
- Class + stream
- Academic year
- Parent/guardian name, phone, email
- Medical notes
- Status: active / archived / transferred / graduated

### Unique Constraints

`UNIQUE(school_id, admission_number)` — no duplicate admission numbers within a school.

---

## 13. Academic Structure

### Hierarchy

```
Academic Year
  └── Term 1, Term 2, Term 3
        ├── Class (e.g., Form 1, Form 2)
        │     └── Stream (e.g., East, West, North, South)
        │           └── Students
        └── Subject (e.g., Mathematics, English)
              └── Department (e.g., Sciences, Languages)
```

### Academic Year

- Defines the school calendar
- Has start/end dates
- One year can be marked `is_current`
- Contains 3 terms (configurable names)

### Classes (Forms/Grades)

- Named (e.g., "Form 1", "Grade 4")
- Optional numeric level for promotion ordering
- Can have multiple streams

### Streams

- Divisions within a class
- Named (e.g., "East", "West", "North", "South")
- Students are assigned to a stream

### Subjects

- Code (e.g., "MAT") + Name (e.g., "Mathematics")
- Optionally belong to a department
- Department groups: Sciences, Languages, Humanities, Technical

---

## 14. Timetable Management

### Structure

- A school has multiple **timetables** (one per academic year)
- Each timetable has **entries** (class slots)
- Entry fields: day_of_week, start_time, end_time, subject, teacher, class, room

### Entry Properties

- Day: 0 (Monday) through 6 (Sunday)
- Time: start_time and end_time (Time type)
- Must have subject, teacher, class, and optional room

### Features

- **Create timetable**: POST with nested entries
- **Add/remove entries**: POST/DELETE individual entries
- **My timetable**: `GET /timetable/my` returns current teacher's entries
- **Conflict detection**: `POST /timetable/check-conflicts` checks if a teacher or class is double-booked

---

## 15. Attendance System

### Recording

- **Batch entry**: `POST /attendance/batch` accepts list of student records
- Per-student fields: status (present/absent/late/excused), remarks
- Recorded by user (audited)
- Date defaults to today
- Enforces unique constraint: one record per student per day

### Viewing

- **Class view**: `GET /attendance/class/{class_id}` for a given date
- **Student history**: `GET /attendance/student/{student_id}` last N days
- **Stats**: `GET /attendance/stats` for class/date summary

### Analytics

- Daily attendance percentage
- Trend over configurable period
- Gender-based analysis
- Integration with advanced dashboard

---

## 16. Gradebook & Assessments

### Assessment Types

| Type | Description |
|------|-------------|
| exam | Formal exam |
| test | Class test |
| quiz | Quick quiz |
| assignment | Graded assignment |
| project | Student project |

### Assessment Properties

- Name, type, max_score, weight
- Links to subject, class, term, teacher
- Optional date_administered + description

### Marks

- One mark per student per assessment
- Fields: score (float), grade (auto-calculated), remarks
- Synced flag for offline recording

### Grade Resolution

Grade is automatically calculated by looking up the school's curriculum grading scheme:

1. Get the school's active curriculum
2. Get the default grading scheme for that curriculum
3. Find the `grade_band` where `min_percentage <= score_percentage <= max_percentage`
4. Return letter grade + points + remark

### Statistics

Per assessment:
- Average score
- Highest score
- Lowest score
- Grade distribution (count per letter grade)

---

## 17. Exams & Results

### Exam Series

- Named exam periods (e.g., "2026 Term 1 CAT")
- Types: CAT, Midterm, End Term, Practical, Project, Mock
- Has weight percentage (contributes to final grade)
- Contains multiple papers

### Exam Papers

- Individual subject papers within a series
- Properties: max_score, weight, duration_minutes, exam_date, instructions
- Paper code for identification

### Exam Scores

- Per-student per-paper: score, grade, is_absent
- Bulk record via `POST /papers/{paper_id}/scores`

### Results & Rankings

- **Student report card**: Full breakdown by subject with scores and grades
- **Class ranking**: Ranked list with mean grades
- **PDF export**: Downloadable report card
- **Class summary**: Aggregated class performance

---

## 18. Lesson Planning

### Lesson Plan Structure

- Topic (required)
- Objectives (learning outcomes)
- Activities (teaching activities)
- Teaching resources (materials needed)
- Assessment (how learning is assessed)
- Homework (assigned work)

### Workflow

- Status: planned → in_progress → completed
- Teachers can mark lessons complete
- Filter by class, subject, completion status

### Duplication

Teachers can duplicate existing lesson plans (for repeated topics across classes/years). The `source_plan_id` field tracks the original.

---

## 19. Curriculum Framework

### Curriculum Library

School Management System comes with pre-loaded curricula that can be assigned to schools:
- KICD (Kenya)
- Nigerian
- South African
- International / Cambridge

Each curriculum contains:
- **Levels**: Ordered progression (e.g., Grade 1→12, Form 1→4)
- **Grading schemes**: Named schemes with grade bands

### Grade Bands

```
Letter  Min %   Max %   Points  Remark
A       80      100     12      Excellent
A-      75      79      11      Very Good
B+      70      74      10      Good
B       65      69      9       Good
B-      60      64      8       Satisfactory
C+      55      59      7       Satisfactory
C       50      54      6       Average
C-      45      49      5       Average
D+      40      44      4       Weak
D       35      39      3       Weak
D-      30      34      2       Poor
E       0       29      1       Fail
```

### Curriculum Assignment

- A school can be assigned ONE active curriculum
- Curriculum assignment triggers creation of school levels
- Grading is resolved via the selected scheme

---

## 20. Assignments & Submissions

### Assignments

Teachers can create assignments for their classes:
- Title, description, type (homework/classwork/project)
- Due date (required)
- Max score (optional)
- Attachments via URL
- Late submission toggle

### Submissions

- Students submit content text and/or file attachments
- Tracked: submission time, late flag
- Teachers can grade with score, grade, and comments
- Grading recorded with timestamp and grader identity

---

## 21. Reports & Analytics

### Standard Reports

| Report | Type | Output |
|--------|------|--------|
| Attendance | Class + date range | JSON/CSV |
| Student List | Class filter | JSON/CSV |
| Teacher Workload | All teachers | JSON |
| Subject Performance | Term filter | JSON |

### Advanced Analytics (Professional+)

| View | Description |
|------|-------------|
| Executive Summary | KPI snapshot (totals, trends) |
| Performance Heatmap | Subject×Class matrix of mean scores |
| At-Risk Students | Students below configurable threshold |
| Term Comparison | Term-over-term performance delta |
| Stream Comparison | Performance across streams in a class |
| Teacher Leaderboard | Teachers ranked by composite score |

### Dashboard Endpoints

- **Admin Dashboard**: `GET /dashboard/admin` — total students, teachers, classes, attendance %, recent assessments
- **Teacher Dashboard**: `GET /dashboard/teacher` — today's timetable, pending attendance, lessons this week
- **Platform Dashboard**: `GET /platform/dashboard` — SaaS-level metrics

---

## 22. Calendar & Scheduling

### Event Types

Calendar events include:
- Timetable entries
- Exam dates
- Assignment due dates
- School events

### Views

- **My calendar** (teacher): `GET /calendar/my` — user's events for a given week
- **School calendar**: `GET /calendar/school` — all school events
- **ICS subscription**: `GET /calendar/my.ics` — subscribable calendar feed
- **Upcoming**: `GET /calendar/upcoming` — events in next N days

---

## 23. Workflow Engine & Approvals

### Concepts

- **Definition**: Template for an approval process (e.g., "Student Transfer Approval")
- **States**: Steps in the process (e.g., "Draft" → "Head Teacher Review" → "Admin Approval" → "Completed")
- **Transitions**: Allowed movements between states
- **Instance**: A running workflow for a specific entity
- **Action**: A state transition action record

### Configuration

Each workflow definition has:
- Entity type (what it applies to)
- State machine with roles required at each state
- Visual config (colors for states)

### State Transitions

Each transition specifies:
- From state → To state
- Action name + display name
- Required role to perform the transition

---

## 24. Audit Logging

### Structure

Every audit log entry captures:
- **When**: `created_at` timestamp
- **Who**: `actor_id`, `actor_role`, `actor_name`
- **Where**: `school_id`, `endpoint`, `ip_address`, `user_agent`
- **What**: `action` (standardized), `entity_type`, `entity_id`
- **Details**: `changes` (JSON diff), `summary` (human-readable text)

### Actions (Standardized)

Account lifecycle actions:
- `teacher_created`, `temp_password_generated`, `first_login_completed`
- `password_changed`, `password_reset_by_admin`
- `account_locked`, `account_unlocked`, `account_disabled`, `account_enabled`
- `failed_login`

Other actions are recorded generically via `entity_type` + `action` strings.

### Querying

- Filter by entity type, action, actor, date range
- Paginated results
- Entity-specific audit trail (`GET /audit/entity/{type}/{id}`)

---

## 25. Import/Export

### CSV Import

| Import Type | Required Fields | Validation |
|-------------|----------------|------------|
| Students | admission_number, full_name, gender, date_of_birth, class | Duplicate admission check, class existence |
| Teachers | full_name, email, employee_number | Duplicate email, duplicate employee number |
| Marks | student_admission, score | assessment_id required, student must exist |

### CSV Export

Available for:
- Teachers list (current search results)
- Attendance reports
- Student lists
- Report cards (PDF)
- Credentials after creation

### Import Flow

```
Upload File
    │
    ▼
Validate (POST /imports/{type}/csv)
    ├── Success → process rows
    └── Error → return row-level errors
              → user can fix and re-upload
    │
    ▼
Return: total_rows, success, skipped, errors[]
```

---

## 26. Student Promotion

### Promotion Flow

```
Select source class
    │
    ▼
Select target class + academic year
    │
    ▼
GET /promotion/path/{class_id} → shows promotion chain
    │
    ▼
POST /promotion/class/{class_id}
  ├── query: target_class_id, target_academic_year_id
  └── optional: min_mean (retention threshold)
    │
    ▼
Result: promoted[], retained[], graduated[], errors[]
```

### What Happens

1. All active students in source class are processed
2. If `min_mean` is set: students below threshold are retained (moved to `retained`)
3. Students at terminal level are marked `graduated`
4. Remaining students are assigned to target class + new academic year
5. If target class has streams, students are distributed

### Rollback

`POST /promotion/rollback` undoes the last promotion operation.

---

## 27. Offline Sync

### Architecture

Designed for schools with intermittent internet connectivity:
- Client tracks changes locally
- On reconnect: `POST /sync/push` sends batched changes
- Server applies changes, detects conflicts, returns server-side changes
- `GET /sync/status` reports pending sync counts

### Conflict Resolution

Server-side wins by default. Conflicting changes are returned to the client for resolution.

---

## 28. Push Notifications

### Device Registration

- Each user can register multiple devices (mobile, web)
- Registration: POST `/push/register` with device token + platform
- Unregistration: POST `/push/unregister`

### Notification Types

- Assignment due date reminders
- Attendance recording reminders
- Approval workflow notifications
- System announcements

### Sending

- POST `/notifications/send` — direct notification
- Channel support: in-app, push, email
- Template-based rendering with variables

---

## 29. Frontend Architecture

### Tech Stack

```
React 18 + TypeScript
├── Vite (build tool)
├── React Router v6 (routing)
├── Zustand (state management)
├── Axios (HTTP client with 401 refresh interceptor)
├── React Hook Form (form validation)
├── React Hot Toast (notifications)
├── Lucide React (icons)
├── clsx (class name utility)
└── Tailwind CSS (styling)
```

### Route Structure

```
/login                          → LoginPage (multi-tenant)
/first-login                    → FirstLoginWizard (password change, contact, TOS)

/admin/*                        → PlatformLayout (dark theme)
  /admin                        → PlatformDashboard
  /admin/schools                → SchoolsPage
  /admin/audit                  → AuditPage
  /admin/billing                → BillingPage
  /admin/settings               → (placeholder)
  /admin/revenue, subscriptions, users, analytics, monitoring,
  health, database, jobs, integrations, feature-flags, backups,
  announcements, support, roles, plans, invoices, payments → (placeholders)

/* (school routes)              → SchoolLayout (blue/green theme)
  /                             → SchoolDashboard
  /dashboard                    → SchoolDashboard
  /students                     → StudentsPage
  /teachers                     → TeachersPage
  /academic                     → AcademicPage
  /timetable                    → TimetablePage
  /attendance                   → AttendancePage
  /gradebook                    → GradebookPage
  /lessons                      → LessonsPage
  /reports                      → ReportsPage
  /exams                        → ExamsPage
  /workflow                     → WorkflowPage
  /curriculum                   → CurriculumPage
  /calendar                     → CalendarView
  /assignments                  → AssignmentManager
  /setup                        → SetupWizard
  /promotion                    → PromotionManager
  /import                       → ImportManager
  /analytics                    → AdvancedDashboard
  /billing                      → BillingPage
  /audit                        → AuditPage
  /staff                        → StaffManagement
  /school/students, /school/teachers, etc. → (aliases for new sidebar links)
```

### Layout Components

| Component | Theme | Audience | Navigation Groups |
|-----------|-------|----------|-------------------|
| PlatformLayout | Dark (gray-950) + purple-600 accents | Platform admins | 5 collapsible sections, 28+ routes |
| SchoolLayout | Emerald-600 branding | School admins + teachers | 4 navigation groups (Main, Academic, Operations, Tools) |

### Auth Store (Zustand)

Persists to `localStorage`:
- `access_token`, `refresh_token`, `user`
- Methods: `login()`, `logout()`, `setTokens()`, `setUser()`

### API Interceptor

Axios interceptor:
- Attaches `Bearer` token to all requests
- On 401: queues requests, attempts `/auth/refresh` with token rotation
- On refresh failure: calls `logout()`

### Responsive Design

- Mobile hamburger menu (mobile-first layout)
- Tablet + desktop sidebar navigation
- Tailwind breakpoints for responsive grids

### Feature Modules

| Module | File | Functionality |
|--------|------|---------------|
| Auth | `features/auth/FirstLoginWizard.tsx` | 3-step first-login wizard |
| Setup | `features/setup/SetupWizard.tsx` | 3-step school onboarding |
| Staff | `features/staff/StaffManagement.tsx` | Teacher management with status badges, lock/unlock, force-reset, bulk operations, import/export |
| Dashboard | `features/dashboard/AdvancedDashboard.tsx` | 4-tab analytics (executive summary, heatmap, at-risk, leaderboard) |
| Assignments | `features/assignments/AssignmentManager.tsx` | Assignment CRUD + submission grading |
| Imports | `features/imports/ImportManager.tsx` | CSV import for students, teachers, marks |
| Calendar | `features/calendar/CalendarView.tsx` | Weekly calendar with ICS export |
| Billing | `features/billing/BillingPage.tsx` | Plans, M-Pesa/Paystack payment, invoice/ payment history |
| Promotion | `features/promotion/PromotionManager.tsx` | Student promotion with rollback |

### Component Library (Custom CSS Classes)

Defined in `styles/index.css`:
- `.btn-primary` — Brand-600 background, white text
- `.btn-secondary` — White background, border
- `.btn-danger` — Red-600 background
- `.input-field` — Standard input with focus ring
- `.label` — Form label
- `.card` — Rounded container with border + shadow
- `.stat-card` — Hover-shadow stat display
- `.page-header` — Responsive flex header row
- `.table-header` / `.table-cell` — Table styling

---

## 30. Security & Compliance

### Authentication Security

- **Argon2id** for password hashing (configurable cost parameters)
- **JWT** with short-lived access tokens (30 min) and revocable refresh tokens (30 days)
- **Failed login lockout**: 5 attempts → 15-minute auto-lock
- **Password history**: last 5 passwords prevented from reuse
- **Session invalidation**: password change/reset clears all refresh tokens

### API Security

- **CORS**: Configurable allowed origins
- **Rate limiting** (placeholder): Endpoint-level rate limiting ready
- **RBAC enforcement**: Every endpoint has a registered permission
- **School scoping**: All queries filter by `school_id`
- **Audit logging**: All account lifecycle events logged

### Data Security

- **Database**: Parameterized queries (SQLAlchemy ORM)
- **Secrets**: All keys/tokens in environment variables, never in code
- **File uploads**: S3-compatible storage, max file size enforcement (10MB default)

### Privacy & Compliance

- **Terms of Service**: Accepted during first-login flow
- **Data isolation**: Complete school-level separation via `school_id`
- **Audit trail**: Immutable logs for all sensitive operations
- **Deletion**: CASCADE deletes ensure no orphaned data when school is removed

### Grade Calculation Validation

Grades are validated against the school's active curriculum's grading scheme at the API layer (not just in the database), ensuring consistency and that grade bands are properly enforced.

---

> **Document Version:** 1.0.0
> **Last Updated:** July 2026
> **Project:** School Management System — Teacher-Centred School Management
