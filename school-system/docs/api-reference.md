# School Management System — API Reference

Base URL: `https://api.example.com/api/v1`

## Authentication

All endpoints except `/auth/login` and `/auth/refresh` require a Bearer token.

### Login

```bash
curl -X POST https://api.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "teacher@school.ac.ke", "password": "teacher123"}'
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "teacher@school.ac.ke",
    "full_name": "Jane Muthoni",
    "role": "teacher",
    "school_id": "660e8400-e29b-41d4-a716-446655440001"
  }
}
```

### Refresh Token

```bash
curl -X POST https://api.example.com/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJhbGciOiJIUzI1NiIs..."}'
```

### All subsequent requests

```bash
curl https://api.example.com/api/v1/students \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

---

## Students

### List Students

```bash
GET /api/v1/students?page=1&page_size=20&search=Ochieng&class_id=CLASS_UUID&status=active
```

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "admission_number": "MSS/2026/001",
      "full_name": "Barack Ochieng",
      "gender": "male",
      "date_of_birth": "2008-05-15",
      "class_id": "uuid",
      "stream_id": "uuid",
      "parent_name": "Jane Ochieng",
      "parent_phone": "+254712345678",
      "status": "active",
      "created_at": "2026-01-05T08:00:00Z"
    }
  ],
  "total": 160,
  "page": 1,
  "page_size": 20
}
```

### Create Student

```bash
POST /api/v1/students
Content-Type: application/json

{
  "admission_number": "MSS/2026/042",
  "full_name": "Amina Hassan",
  "gender": "female",
  "date_of_birth": "2009-03-22",
  "class_id": "uuid",
  "stream_id": "uuid",
  "academic_year_id": "uuid",
  "parent_name": "Hassan Ali",
  "parent_phone": "+254723456789",
  "medical_notes": "Mild asthma"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| admission_number | string | ✅ | Unique per school |
| full_name | string | ✅ | |
| gender | string | ✅ | "male", "female", or "other" |
| date_of_birth | date | ✅ | YYYY-MM-DD |
| class_id | uuid | ✅ | |
| academic_year_id | uuid | ✅ | |
| stream_id | uuid | | |
| parent_name | string | | |
| parent_phone | string | | |
| parent_email | email | | |
| medical_notes | string | | |

### Promote Student

```bash
POST /api/v1/students/{student_id}/promote
Content-Type: application/json

{
  "target_class_id": "uuid",
  "target_academic_year_id": "uuid"
}
```

### Archive Student

```bash
POST /api/v1/students/{student_id}/archive
```

### Bulk Promote Class

```bash
POST /api/v1/promotion/class/{class_id}?target_class_id=UUID&target_academic_year_id=UUID&min_mean=35
```

**Response:**
```json
{
  "promoted": 38,
  "retained": 2,
  "graduated": 0,
  "errors": []
}
```

---

## Attendance

### Record Attendance (Batch)

```bash
POST /api/v1/attendance/batch
Content-Type: application/json

{
  "class_id": "uuid",
  "attendance_date": "2026-07-12",
  "records": [
    {"student_id": "uuid", "status": "present"},
    {"student_id": "uuid", "status": "absent", "remarks": "Sick"},
    {"student_id": "uuid", "status": "late"},
    {"student_id": "uuid", "status": "excused", "remarks": "Family event"}
  ]
}
```

**Valid statuses:** `present`, `absent`, `late`, `excused`

### Get Class Attendance

```bash
GET /api/v1/attendance/class/{class_id}?attendance_date=2026-07-12
```

**Response:**
```json
{
  "records": [...],
  "stats": {
    "total_students": 40,
    "present": 35,
    "absent": 2,
    "late": 1,
    "excused": 1,
    "percentage": 87.5
  }
}
```

---

## Gradebook & Marks

### Create Assessment

```bash
POST /api/v1/gradebook/assessments
Content-Type: application/json

{
  "subject_id": "uuid",
  "class_id": "uuid",
  "term_id": "uuid",
  "name": "Mathematics Mid-Term",
  "assessment_type": "exam",
  "max_score": 100,
  "weight": 1.0,
  "date_administered": "2026-02-15"
}
```

**Assessment types:** `exam`, `test`, `quiz`, `assignment`, `project`

### Record Marks (Batch)

```bash
POST /api/v1/gradebook/assessments/{assessment_id}/marks
Content-Type: application/json

[
  {"student_id": "uuid", "score": 85, "remarks": "Good work"},
  {"student_id": "uuid", "score": 72}
]
```

### Get Assessment Stats

```bash
GET /api/v1/gradebook/assessments/{assessment_id}/stats
```

**Response:**
```json
{
  "assessment_id": "uuid",
  "total_students": 40,
  "average": 67.3,
  "highest": 98,
  "lowest": 22,
  "class_average": 67.3,
  "grade_distribution": {
    "A": 5, "A-": 3, "B+": 7, "B": 8, "C": 10, "D": 4, "E": 3
  }
}
```

---

## Exams

### Create Exam Series

```bash
POST /api/v1/exams/series
Content-Type: application/json

{
  "term_id": "uuid",
  "name": "Term 1 End of Term Exams",
  "series_type": "endterm",
  "start_date": "2026-03-20",
  "end_date": "2026-03-28",
  "weight_percentage": 40.0
}
```

**Series types:** `cat`, `midterm`, `endterm`, `practical`, `project`, `mock`

### Create Exam Paper

```bash
POST /api/v1/exams/papers
Content-Type: application/json

{
  "series_id": "uuid",
  "subject_id": "uuid",
  "class_id": "uuid",
  "name": "Mathematics Paper 1",
  "paper_code": "P1",
  "max_score": 100,
  "weight": 1.0,
  "duration_minutes": 150,
  "exam_date": "2026-03-22"
}
```

### Record Exam Scores

```bash
POST /api/v1/exams/papers/{paper_id}/scores
Content-Type: application/json

[
  {"student_id": "uuid", "score": 78, "is_absent": false},
  {"student_id": "uuid", "score": 0, "is_absent": true, "remarks": "Sick"}
]
```

### Class Exam Ranking

```bash
GET /api/v1/exams/results/class/{class_id}/ranking?term_id=uuid
```

**Response:**
```json
{
  "rankings": [
    {"student_id": "uuid", "name": "Student Name", "admission_number": "MSS/001",
     "mean": 82.5, "grade": "A", "points": 12, "rank": 1},
    ...
  ],
  "total": 40
}
```

---

## Lesson Plans

### Create Lesson

```bash
POST /api/v1/lessons
Content-Type: application/json

{
  "subject_id": "uuid",
  "class_id": "uuid",
  "topic": "Quadratic Equations",
  "objectives": "Students will solve quadratic equations by factorization",
  "activities": "Guided practice, group work, board exercises",
  "teaching_resources": "Textbook pp 45-52, whiteboard, graph paper",
  "assessment": "Exit ticket: solve 3 equations",
  "homework": "Exercise 4.2, questions 1-10",
  "week_number": 5,
  "term_number": 1
}
```

### Duplicate Lesson

```bash
POST /api/v1/lessons/duplicate
Content-Type: application/json

{
  "source_plan_id": "uuid",
  "class_id": "uuid"
}
```

### Mark Complete

```bash
POST /api/v1/lessons/{lesson_id}/complete
```

---

## Reports

### Generate Attendance Report

```bash
GET /api/v1/reports/attendance?class_id=UUID&from_date=2026-01-01&to_date=2026-04-01&format=json
```

Set `format=csv` for CSV download.

### Generate Student List

```bash
GET /api/v1/reports/students?class_id=UUID&format=csv
```

### Teacher Workload

```bash
GET /api/v1/reports/teacher-workload
```

### Subject Performance

```bash
GET /api/v1/reports/subject-performance?term_id=UUID
```

---

## Results & Report Cards

### Student Report Card (JSON)

```bash
GET /api/v1/results/student/{student_id}/report-card?term_id=uuid
```

### Download PDF Report Card

```bash
GET /api/v1/results/student/{student_id}/report-card/pdf?term_id=uuid
```

Returns a downloadable PDF file.

### Class Summary

```bash
GET /api/v1/results/class/{class_id}/summary?term_id=uuid
```

### Class Rankings

```bash
GET /api/v1/results/class/{class_id}/rankings?term_id=uuid
```

---

## Analytics

### School Overview

```bash
GET /api/v1/analytics/overview
```

### Attendance Trend

```bash
GET /api/v1/analytics/attendance-trend?days=30
```

### Gender Analysis

```bash
GET /api/v1/analytics/gender-analysis?term_id=uuid
```

### Syllabus Coverage

```bash
GET /api/v1/analytics/syllabus-coverage?teacher_id=UUID&subject_id=UUID
```

### Teacher Effectiveness

```bash
GET /api/v1/analytics/teacher-effectiveness?term_id=uuid
```

---

## Advanced Dashboard

### Executive Summary

```bash
GET /api/v1/dashboard/advanced/executive-summary
```

### Performance Heatmap

```bash
GET /api/v1/dashboard/advanced/performance-heatmap?term_id=uuid
```

### At-Risk Students

```bash
GET /api/v1/dashboard/advanced/at-risk-students?term_id=uuid&threshold=40
```

### Term Comparison

```bash
GET /api/v1/dashboard/advanced/term-comparison?term1_id=uuid&term2_id=uuid
```

### Stream Comparison

```bash
GET /api/v1/dashboard/advanced/stream-comparison?class_id=uuid&term_id=uuid
```

### Teacher Leaderboard

```bash
GET /api/v1/dashboard/advanced/teacher-leaderboard?term_id=uuid
```

---

## Curriculum

### List Curricula

```bash
GET /api/v1/curriculum
```

Returns 6 curricula: CBC Kenya, 8-4-4 Kenya, Cambridge IGCSE, IB Diploma, Nigeria BEC, South Africa CAPS.

### View Curriculum Detail

```bash
GET /api/v1/curriculum/{curriculum_id}
```

### Assign Curriculum to School

```bash
POST /api/v1/curriculum/assign?curriculum_id=uuid
```

### Compute Grade

```bash
GET /api/v1/curriculum/my/grade?percentage=72
```

**Response:**
```json
{
  "percentage": 72,
  "letter": "B+",
  "points": 10,
  "remark": "Very Good"
}
```

---

## Mobile API (Compact Payloads)

All mobile endpoints accept `?since=ISO_DATETIME` for delta sync.

### Today's Summary

```bash
GET /api/v1/mobile/today
```

### My Students (Compact)

```bash
GET /api/v1/mobile/my-students?since=2026-07-01T00:00:00Z
```

### Quick Attendance (Compact)

```bash
POST /api/v1/mobile/quick-attendance
Content-Type: application/json

{
  "class_id": "uuid",
  "date": "2026-07-12",
  "records": [
    {"s": "student-uuid", "st": "present"},
    {"s": "student-uuid", "st": "absent", "r": "Sick"}
  ]
}
```
Fields: `s`=student_id, `st`=status, `r`=remarks

### Quick Marks (Compact)

```bash
POST /api/v1/mobile/quick-marks
Content-Type: application/json

{
  "assessment_id": "uuid",
  "marks": [
    {"s": "student-uuid", "sc": 85},
    {"s": "student-uuid", "sc": 72}
  ]
}
```
Fields: `s`=student_id, `sc`=score

### Sync Checkpoint

```bash
GET /api/v1/mobile/sync-checkpoint
```

---

## Workflow

### List Workflows

```bash
GET /api/v1/workflow/definitions
```

### View Workflow States

```bash
GET /api/v1/workflow/definitions/{workflow_id}
```

### Execute Transition

```bash
POST /api/v1/workflow/instances/{instance_id}/transition?action=approve&comment=LGTM
```

### Available Actions

```bash
GET /api/v1/workflow/instances/{instance_id}/actions
```

### Workflow History

```bash
GET /api/v1/workflow/instances/{instance_id}/history
```

---

## Audit Trail

### Query Audit Logs

```bash
GET /api/v1/audit?entity_type=mark&action=update&page=1&page_size=50
```

### Entity History

```bash
GET /api/v1/audit/entity/student/{student_id}
```

---

## Public API (Third-Party)

Authenticate with `X-API-Key` header.

```bash
curl https://api.example.com/public/v1/students \
  -H "X-API-Key: your-api-key"
```

| Endpoint | Description |
|----------|-------------|
| `GET /public/v1/students` | List students with filters |
| `GET /public/v1/students/{id}` | Single student |
| `GET /public/v1/attendance` | Attendance records |
| `GET /public/v1/marks` | Marks/grades |
| `GET /public/v1/teachers` | Teacher roster |
| `POST /public/v1/webhooks/attendance` | Receive from biometric devices |

---

## Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No content (success, no body) |
| 400 | Bad request — check your payload |
| 401 | Unauthorized — invalid or expired token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not found |
| 409 | Conflict — duplicate unique field |
| 422 | Validation error |
| 423 | Account locked (too many failed logins) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/auth/login` | 5 requests/minute per IP |
| `/api/*` (general) | 10 requests/second per IP |
| `/public/*` | 1000 requests/minute per API key |

---

## Permission Matrix

| Role | Students | Teachers | Marks | Attendance | Reports | Settings |
|------|----------|----------|-------|------------|---------|----------|
| platform_admin | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All |
| school_admin | ✅ CRUD | ✅ CRUD | ✅ Read | ✅ Read | ✅ Export | ✅ Manage |
| deputy_principal | ✅ Read | ✅ Read | ✅ Read | ✅ Read | ✅ Export | ❌ |
| head_teacher | ✅ Promote | ✅ Read | ✅ Read | ✅ Read | ✅ Export | ❌ |
| class_teacher | ✅ Read | ❌ | ✅ Write | ✅ Write | ✅ View | ❌ |
| subject_teacher | ✅ Read | ❌ | ✅ Write | ❌ | ✅ View | ❌ |
| teacher | ✅ Read | ❌ | ✅ Write | ✅ Write | ❌ | ❌ |
