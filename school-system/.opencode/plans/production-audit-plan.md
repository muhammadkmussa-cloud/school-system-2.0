# School Management System — Complete Production Audit Plan

## Overview
- Backend: 108 Python files, ~12,720 lines
- Frontend: 28 TS/TSX files, ~4,305 lines
- Tests: 12 files, ~1,689 lines
- Previous fixes: 12 critical bugs, N+1 in results_engine, grading consolidation, security middleware, exam/billing schemas

---

## RED TIER 1 — Critical (Fix Immediately, ~8h)

### 1.1 DB Integrity — 23 Foreign Keys Missing `ondelete`
**Fix:** Add `ondelete="SET NULL"` (optional) or `ondelete="CASCADE"` (ownership) across: student.py (class_id, stream_id, academic_year_id), timetable.py (subject_id, teacher_id, class_id), attendance.py (class_id, recorded_by), assessment.py (subject_id, teacher_id, class_id, term_id), lesson.py (teacher_id, subject_id, class_id), assignment.py (teacher_id, subject_id, class_id, graded_by), exam.py (term_id, subject_id, class_id), workflow.py (actor_id).

### 1.2 Tenant Isolation — 9 Models Missing `school_id`
Models: Term, TimetableEntry, AttendanceRecord, Mark, AssignmentSubmission, ExamPaper, ExamScore, WorkflowInstance, WorkflowAction
**Fix:** Add `school_id = Column(ForeignKey("schools.id", ondelete="CASCADE"))` to each.

### 1.3 API Tenant Isolation — 8 Endpoints
- `POST /academic/terms` (v1/academic.py:97-105) — Term created without school_id
- `GET /exams/papers/{series_id}` (v1/exams.py:86) — No school_id filter
- `POST /exams/papers` (v1/exams.py:64-81) — No series school check
- `GET /workflow/definitions/{id}` (v1/workflow.py:37-61) — No school_id filter
- `POST /billing/mpesa/query` (v1/billing.py:172-178) — **No authentication**
- `GET /billing/paystack/verify` (v1/billing.py:197-202) — **No authentication**
- `POST /mobile/quick-attendance` (mobile/router.py:148-195) — No school check
- `POST /mobile/quick-marks` (mobile/router.py:200-245) — No school check

### 1.4 Grade Threshold Inconsistency
advanced_dashboard.py:222 — `_grade_from_mean()` uses 80/65/50/35 hardcoded
**Fix:** Use `app.core.grading.grade_for()` instead.

### 1.5 Duplicate Mean Computation (3 copies)
results_engine.py:289, promotion_service.py:140, advanced_dashboard.py:272
**Fix:** Extract to `app/core/grading.py` as `compute_weighted_mean()`.

### 1.6 sync_service Bug
sync_service.py:223 — `db.scalar(select(...))` returns ORM object not count
**Fix:** Use `select(func.count())`.

### 1.7 Dead Code — 225 Lines
Delete: `services/base.py` (113 lines), `services/edge_cases/grading_edge_cases.py` (112 lines)

### 1.8 Private Method Call
api/v1/results.py:103 calls `engine._compute_mean_for_student()`
**Fix:** Rename to public `compute_mean_for_student()`.

### 1.9 timedelta Import Bug
onboarding_service.py — `timedelta` imported at line 209, used at line 140
**Fix:** Move import to top of file.

### 1.10 Orphaned FK Bug
importer.py:120 — `year_id or uuid.uuid4()` creates orphaned FK
**Fix:** Raise `ValueError("Could not resolve academic year")`.

---

## ORANGE TIER 2 — High Priority (~16h)

### 2.1 Frontend Auth Downloads (3 broken)
ReportsPage.tsx:22, CalendarView.tsx:39, ImportManager.tsx:44 use window.open() (no auth)
**Fix:** Use Axios `responseType: 'blob'` + `URL.createObjectURL()`.

### 2.2 Missing Marks Template Endpoint
backend needs `GET /imports/templates/marks`.

### 2.3 ExamsPage Static Class
ExamsPage.tsx:48 always uses classes[0].id for rankings
**Fix:** Add class selector dropdown.

### 2.4 AdvancedDashboard Heatmap
AdvancedDashboard.tsx:153 — placeholder, never calls API
**Fix:** Wire up performance-heatmap endpoint.

### 2.5 Gradebook Isolation (3 endpoints)
v1/gradebook.py:138-223 — marks, stats, grades lack school_id.

### 2.6 Attendance Isolation (1 endpoint)
v1/attendance.py:118-137 — GET /student/{id} no school_id filter.

### 2.7 Push Service — Tokens In-Memory
push_service.py:40 — class-level dict lost on restart
**Fix:** Store in DB.

### 2.8 Notification Service — Stub
notification_service.py — in-memory, stub email/SMS
**Fix:** Add DB persistence or warning.

### 2.9 Audit Service Unused
audit_service.py — never called from mutations
**Fix:** Wire into create/update/delete endpoints.

### 2.10 N+1 Queries (6+ patterns)
analytics_service.py + advanced_dashboard.py
**Fix:** Batch-load with in_() queries.

### 2.11 CurriculumPage Bug
CurriculumPage.tsx:147 — object reference always true
**Fix:** Use index comparison.

### 2.12 Missing ORM Relationships (11 gaps)
School (9 missing back-refs), LessonPlan (class_ rel), Assignment (4 rels), WorkflowTransition (to_state), ExamScore (student), AttendanceRecord (recorder back_populates), SchoolCurriculum (0 rels)

---

## YELLOW TIER 3 — Medium Priority (~12h)

3.1 Unenforced FKs: source_plan_id, promotion_to_level_id
3.2 Type mismatches: assessment.py:39, billing.py:63
3.3 Assignments pagination broken (assignments.py:19)
3.4 Unused imports: 13 backend + 12 frontend files
3.5 Missing response_model: 50+ endpoints
3.6 Raw dict bodies: 15 remaining endpoints
3.7 Missing TS interfaces: 12+ entity types
3.8 any types: 11 frontend components
3.9 Orphan /analytics route
3.10 Missing UniqueConstraints (Stream, Subject)
3.11 Clean __pycache__ dirs

---

## GREEN TIER 4 — Low Priority (~8h)

4.1 Form validation (email, phone, numeric bounds)
4.2 LoginHistory missing TimestampMixin
4.3 Hardcoded remarks in results_engine
4.4 Hardcoded colors in pdf_report_card
4.5 ICS feed missing UTC tz
4.6 SetupWizard hardcoded 2026 dates
4.7 Password strength validation

---

## SCORES

| Metric | Score |
|--------|-------|
| Architecture | 85/100 |
| Code Consistency | 60/100 |
| Security | 70/100 |
| Testing | 40/100 |
| Frontend Completeness | 65/100 |
| API Design | 75/100 |
| Data Layer | 60/100 |
| **Overall** | **65/100** |
| **Production Readiness** | **65/100** |
| **Technical Debt** | **~44 hours (41 items)** |
