#!/usr/bin/env python3
"""School Management System — Performance Benchmark Suite.

Runs realistic workloads against the database and measures throughput.
Simulates: 1,000 student attendance batch, 500 mark insertions,
report card generation, class ranking computation.

Usage:
    python -m benchmarks.bench_runner --students 1000 --marks 500
"""

from __future__ import annotations

import argparse
import asyncio
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from sqlalchemy import select, func, text

from app.core.database import async_session_factory, engine, Base
from app.models.school import School
from app.models.student import Student
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark
from app.models.academic import Class_, AcademicYear, Subject, Term
from app.models.user import User


@dataclass
class BenchmarkResult:
    name: str
    duration_ms: float
    operations: int
    ops_per_sec: float = 0.0
    details: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.duration_ms > 0:
            self.ops_per_sec = self.operations / (self.duration_ms / 1000)


BENCH_RESULTS: list[BenchmarkResult] = []


def _now() -> float:
    return time.perf_counter()


async def setup_test_data(student_count: int = 1000):
    """Create test school, class, students for benchmarks."""
    async with async_session_factory() as db:
        async with db.begin():
            school = School(id=uuid.uuid4(), name="Benchmark School", code="BENCH", is_active=True)
            db.add(school)
            await db.flush()

            ay = AcademicYear(id=uuid.uuid4(), school_id=school.id, name="Bench Year",
                              start_date=date(2026,1,1), end_date=date(2026,12,31))
            klass = Class_(id=uuid.uuid4(), school_id=school.id, name="Bench Class", level=1)
            term = Term(id=uuid.uuid4(), academic_year_id=ay.id, name="T1",
                        term_number=1, start_date=date(2026,1,1), end_date=date(2026,4,1))
            subj = Subject(id=uuid.uuid4(), school_id=school.id, code="BEN", name="Bench Subject")
            user = User(id=uuid.uuid4(), school_id=school.id, email="bench@test.com",
                        hashed_password="x", full_name="Bench", role="teacher")

            db.add_all([ay, klass, term, subj, user])
            await db.flush()

            # Batch insert students
            students = []
            for i in range(student_count):
                students.append(Student(
                    id=uuid.uuid4(), school_id=school.id,
                    admission_number=f"BENCH-{i:06d}", full_name=f"Bench Student {i}",
                    gender=random.choice(["male", "female"]),
                    date_of_birth=date(2008, 1, 1),
                    class_id=klass.id, academic_year_id=ay.id, status="active",
                ))
            db.add_all(students)

        return {
            "school_id": school.id,
            "class_id": klass.id,
            "term_id": term.id,
            "subject_id": subj.id,
            "user_id": user.id,
        }


async def bench_attendance_batch(ids: dict, count: int):
    """Benchmark: insert N attendance records in one batch."""
    async with async_session_factory() as db:
        # Get student IDs
        students = (await db.scalars(
            select(Student.id).where(Student.school_id == ids["school_id"]).limit(count)
        )).all()

        start = _now()
        records = []
        today = date.today()
        for sid in students:
            records.append(AttendanceRecord(
                student_id=sid, class_id=ids["class_id"],
                recorded_by=ids["user_id"], attendance_date=today,
                status=random.choice(["present", "absent"]),
            ))
        db.add_all(records)
        await db.flush()
        await db.commit()
        elapsed = (_now() - start) * 1000

        result = BenchmarkResult(
            name=f"Attendance Batch ({len(records)} records)",
            duration_ms=round(elapsed, 2),
            operations=len(records),
        )
        BENCH_RESULTS.append(result)
        return result


async def bench_mark_insertion(ids: dict, count: int):
    """Benchmark: create assessment + insert N marks."""
    async with async_session_factory() as db:
        assessment = Assessment(
            id=uuid.uuid4(), school_id=ids["school_id"],
            subject_id=ids["subject_id"], teacher_id=ids["user_id"],
            class_id=ids["class_id"], term_id=ids["term_id"],
            name="Bench Assessment", assessment_type="exam",
            max_score=100, weight=1.0,
        )
        db.add(assessment)
        await db.flush()

        students = (await db.scalars(
            select(Student.id).where(Student.school_id == ids["school_id"]).limit(count)
        )).all()

        start = _now()
        marks = []
        for sid in students:
            marks.append(Mark(
                assessment_id=assessment.id, student_id=sid,
                score=round(random.uniform(20, 98), 1),
            ))
        db.add_all(marks)
        await db.flush()
        await db.commit()
        elapsed = (_now() - start) * 1000

        result = BenchmarkResult(
            name=f"Mark Insertion ({len(marks)} marks)",
            duration_ms=round(elapsed, 2),
            operations=len(marks),
        )
        BENCH_RESULTS.append(result)
        return result


async def bench_student_query(ids: dict, iterations: int = 100):
    """Benchmark: query students with pagination N times."""
    async with async_session_factory() as db:
        start = _now()
        for _ in range(iterations):
            await db.scalars(
                select(Student)
                .where(Student.school_id == ids["school_id"], Student.status == "active")
                .order_by(Student.full_name)
                .limit(50)
            )
        elapsed = (_now() - start) * 1000

        result = BenchmarkResult(
            name=f"Student Query ({iterations} queries)",
            duration_ms=round(elapsed, 2),
            operations=iterations,
        )
        BENCH_RESULTS.append(result)
        return result


async def bench_count_aggregate(ids: dict, iterations: int = 50):
    """Benchmark: COUNT queries with joins."""
    async with async_session_factory() as db:
        start = _now()
        for _ in range(iterations):
            await db.scalar(select(func.count(Student.id)).where(
                Student.school_id == ids["school_id"], Student.status == "active"
            ))
            await db.scalar(
                select(func.count(AttendanceRecord.id)).join(Student).where(
                    Student.school_id == ids["school_id"]
                )
            )
        elapsed = (_now() - start) * 1000

        result = BenchmarkResult(
            name=f"Aggregate Queries ({iterations * 2} queries)",
            duration_ms=round(elapsed, 2),
            operations=iterations * 2,
        )
        BENCH_RESULTS.append(result)
        return result


async def bench_db_ping(iterations: int = 200):
    """Benchmark: raw connection ping."""
    async with async_session_factory() as db:
        start = _now()
        for _ in range(iterations):
            await db.execute(text("SELECT 1"))
        elapsed = (_now() - start) * 1000

        result = BenchmarkResult(
            name=f"DB Ping ({iterations} pings)",
            duration_ms=round(elapsed, 2),
            operations=iterations,
        )
        BENCH_RESULTS.append(result)
        return result


async def run_all_benchmarks(student_count: int, mark_count: int):
    """Run the full benchmark suite."""
    print(f"\n{'='*60}")
    print(f"  School Management System — Performance Benchmarks")
    print(f"  Students: {student_count}  |  Marks: {mark_count}")
    print(f"{'='*60}\n")

    ids = await setup_test_data(student_count)

    await bench_db_ping(200)
    await bench_student_query(ids, 100)
    await bench_count_aggregate(ids, 50)
    await bench_attendance_batch(ids, min(student_count, 1000))
    await bench_mark_insertion(ids, min(mark_count, 500))

    print(f"\n{'─'*60}")
    print(f"  {'Benchmark':<35} {'Time':>8}  {'Ops/sec':>10}")
    print(f"{'─'*60}")
    for r in BENCH_RESULTS:
        print(f"  {r.name:<35} {r.duration_ms:>7.1f}ms  {r.ops_per_sec:>9.0f}/s")
    print(f"{'─'*60}")

    total = sum(r.duration_ms for r in BENCH_RESULTS)
    total_ops = sum(r.operations for r in BENCH_RESULTS)
    print(f"  {'TOTAL':<35} {total:>7.1f}ms  {total_ops / (total / 1000):>9.0f}/s")
    print(f"{'─'*60}\n")

    # Performance recommendations
    slowest = max(BENCH_RESULTS, key=lambda r: r.duration_ms)
    if slowest.ops_per_sec < 500:
        print(f"⚠️  Slowest: '{slowest.name}' at {slowest.ops_per_sec:.0f} ops/sec")
        print("   Consider: database indexing, connection pooling, or batch processing.\n")

    return BENCH_RESULTS


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="School Management System Performance Benchmarks")
    parser.add_argument("--students", type=int, default=1000, help="Number of test students")
    parser.add_argument("--marks", type=int, default=500, help="Number of test marks")
    args = parser.parse_args()

    # Create tables if they don't exist
    async def _ensure_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_ensure_tables())
    asyncio.run(run_all_benchmarks(args.students, args.marks))
