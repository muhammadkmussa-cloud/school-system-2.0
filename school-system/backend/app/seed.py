#!/usr/bin/env python3
"""School Management System — Database Seeder.

Creates a demo school with a full academic structure, teachers,
students, and sample data for testing and demos.

Usage:
    python -m app.seed          # seeds the database
    python -m app.seed --reset  # drops everything first
"""

from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from datetime import date, time, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, async_session_factory, engine
from app.core.security import hash_password
from app.models.academic import (
    AcademicYear,
    Class_,
    Department,
    Stream,
    Subject,
    Term,
)
from app.models.assessment import Assessment, Mark
from app.models.attendance import AttendanceRecord
from app.models.lesson import LessonPlan
from app.models.school import School
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.timetable import Timetable, TimetableEntry
from app.models.user import User
from app.models.curriculum import SchoolCurriculum
from app.services.curriculum.curriculum_service import CurriculumService
from app.services.workflow.workflow_engine import WorkflowEngine

# ── Kenyan-style names ──────────────────────────────────────────────
FIRST_NAMES = [
    "Wanjiku", "Amina", "Barack", "Chioma", "Dayo", "Emeka",
    "Fatima", "Gideon", "Halima", "Ifeanyi", "Jamal", "Kendi",
    "Lilian", "Mwangi", "Nala", "Ochieng", "Pendo", "Rashid",
    "Safiya", "Tendai", "Uche", "Vivian", "Wekesa", "Zuri",
    "Akinyi", "Bakari", "Chidi", "Daudi", "Eshe", "Femi",
    "Kamau", "Nia", "Odhiambo", "Pili", "Sefu", "Thandiwe",
    "Adisa", "Chinua", "Ngozi", "Obi", "Mandela", "Lumumba",
]
LAST_NAMES = [
    "Kamau", "Omondi", "Wanjala", "Nyambura", "Toure", "Okonkwo",
    "Mwangi", "Chebet", "Ndlovu", "Adhiambo", "Diallo", "Nwosu",
    "Otieno", "Wafula", "Achebe", "Soyinka", "Biko", "Selassie",
    "Kiprotich", "Akello", "Mugisha", "Ndung'u", "Were", "Chirwa",
]

SUBJECTS_DATA = [
    ("MAT", "Mathematics", "Sciences"),
    ("ENG", "English", "Languages"),
    ("KIS", "Kiswahili", "Languages"),
    ("BIO", "Biology", "Sciences"),
    ("CHE", "Chemistry", "Sciences"),
    ("PHY", "Physics", "Sciences"),
    ("HIS", "History", "Humanities"),
    ("GEO", "Geography", "Humanities"),
    ("CRE", "Christian Religious Education", "Humanities"),
    ("BSN", "Business Studies", "Technical"),
    ("AGR", "Agriculture", "Technical"),
    ("CMP", "Computer Studies", "Technical"),
]

CLASSES_DATA = [
    ("Form 1", 1),
    ("Form 2", 2),
    ("Form 3", 3),
    ("Form 4", 4),
]

STREAMS_DATA = ["East", "West", "North", "South"]


async def seed(reset: bool = False):
    async with engine.begin() as conn:
        if reset:
            await conn.run_sync(Base.metadata.drop_all)
            print("🗑️  All tables dropped.")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tables created.")

    async with async_session_factory() as db:
        # ── School ───────────────────────────────────────────────
        school = School(
            name="Mombasa Secondary School",
            code="MSS-001",
            email="admin@example.com",
            phone="+254712345678",
            address="123 Moi Avenue, Mombasa, Kenya",
            is_active=True,
            subscription_tier="demo",
        )
        db.add(school)
        await db.flush()
        print(f"🏫 School: {school.name}")

        # ── Platform Admin ───────────────────────────────────────
        platform_admin = User(
            school_id=school.id,
            email="platform@example.com",
            hashed_password=hash_password("admin123"),
            full_name="Platform Administrator",
            role="platform_admin",
            is_active=True,
            is_verified=True,
        )
        db.add(platform_admin)

        # ── School Admin ─────────────────────────────────────────
        school_admin = User(
            school_id=school.id,
            email="admin@example.com",
            hashed_password=hash_password("admin123"),
            full_name="Jane Wanjiku",
            role="school_admin",
            is_active=True,
            is_verified=True,
        )
        db.add(school_admin)
        await db.flush()

        # ── Academic Year ────────────────────────────────────────
        acad_year = AcademicYear(
            school_id=school.id,
            name="2026 Academic Year",
            start_date=date(2026, 1, 5),
            end_date=date(2026, 12, 18),
            is_current=True,
        )
        db.add(acad_year)
        await db.flush()

        # ── Terms ────────────────────────────────────────────────
        terms_data = [
            ("Term 1", 1, date(2026, 1, 5), date(2026, 4, 3), True),
            ("Term 2", 2, date(2026, 5, 4), date(2026, 8, 7), False),
            ("Term 3", 3, date(2026, 9, 7), date(2026, 12, 18), False),
        ]
        terms = {}
        for name, num, start, end, current in terms_data:
            term = Term(
                school_id=school.id,
                academic_year_id=acad_year.id,
                name=name,
                term_number=num,
                start_date=start,
                end_date=end,
                is_current=current,
            )
            db.add(term)
            await db.flush()
            terms[num] = term

        # ── Departments ──────────────────────────────────────────
        dept_names = ["Sciences", "Languages", "Humanities", "Technical"]
        departments = {}
        for name in dept_names:
            dept = Department(school_id=school.id, name=name)
            db.add(dept)
            await db.flush()
            departments[name] = dept

        # ── Subjects ─────────────────────────────────────────────
        subjects = {}
        for code, name, dept_name in SUBJECTS_DATA:
            subj = Subject(
                school_id=school.id,
                department_id=departments[dept_name].id,
                code=code,
                name=name,
            )
            db.add(subj)
            await db.flush()
            subjects[code] = subj

        # ── Classes & Streams ────────────────────────────────────
        classes = {}
        streams = {}
        for class_name, level in CLASSES_DATA:
            klass = Class_(
                school_id=school.id,
                name=class_name,
                level=level,
            )
            db.add(klass)
            await db.flush()
            classes[class_name] = klass

            for stream_name in STREAMS_DATA:
                stream = Stream(
                    school_id=school.id,
                    class_id=klass.id,
                    name=stream_name,
                )
                db.add(stream)
                await db.flush()
                streams[f"{class_name}-{stream_name}"] = stream

        # ── Teachers ─────────────────────────────────────────────
        teachers = {}
        for i in range(8):
            emp_no = f"TSC-{2026000 + i}"
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            full_name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}@example.com"

            user = User(
                school_id=school.id,
                email=email,
                hashed_password=hash_password("teacher123"),
                full_name=full_name,
                role="teacher",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()

            teacher = Teacher(
                school_id=school.id,
                user_id=user.id,
                employee_number=emp_no,
                full_name=full_name,
                email=email,
                phone=f"+2547{random.randint(10000000, 99999999)}",
            )
            db.add(teacher)
            await db.flush()
            teachers[emp_no] = teacher

        # ── Students ─────────────────────────────────────────────
        students_all = []
        for class_name, level in CLASSES_DATA:
            klass = classes[class_name]
            class_streams = [
                s for k, s in streams.items() if k.startswith(class_name)
            ]

            for i in range(40):  # 40 students per class
                fname = random.choice(FIRST_NAMES)
                lname = random.choice(LAST_NAMES)
                gender = random.choice(["male", "female"])
                stream = random.choice(class_streams)
                adm = f"MSS-{2026}{level:02d}{i:03d}"

                student = Student(
                    school_id=school.id,
                    admission_number=adm,
                    full_name=f"{fname} {lname}",
                    gender=gender,
                    date_of_birth=date(
                        random.randint(2006, 2010),
                        random.randint(1, 12),
                        random.randint(1, 28),
                    ),
                    class_id=klass.id,
                    stream_id=stream.id,
                    academic_year_id=acad_year.id,
                    parent_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    parent_phone=f"+2547{random.randint(10000000, 99999999)}",
                    status="active",
                )
                db.add(student)
                await db.flush()
                students_all.append(student)

        print(f"👩‍🎓 Created {len(students_all)} students, {len(teachers)} teachers")

        # ── Timetable ────────────────────────────────────────────
        timetable = Timetable(
            school_id=school.id,
            academic_year_id=acad_year.id,
            name="Term 1 Master Timetable",
            is_active=True,
        )
        db.add(timetable)
        await db.flush()

        subject_list = list(subjects.values())
        teacher_list = list(teachers.values())
        for day in range(5):  # Mon–Fri
            for hour in range(8, 16):  # 8 AM – 4 PM
                klass_idx = (day + hour) % len(classes)
                klass = list(classes.values())[klass_idx]
                subj = subject_list[(day * 7 + hour) % len(subject_list)]
                tchr = teacher_list[(day * 3 + hour) % len(teacher_list)]
                entry = TimetableEntry(
                    school_id=school.id,
                    timetable_id=timetable.id,
                    day_of_week=day,
                    start_time=time(hour, 0),
                    end_time=time(hour, 40),
                    subject_id=subj.id,
                    teacher_id=tchr.id,
                    class_id=klass.id,
                    room=f"R{100 + hour}",
                )
                db.add(entry)

        # ── Attendance (last 14 days) ────────────────────────────
        for days_ago in range(14):
            att_date = date.today() - timedelta(days=days_ago)
            if att_date.weekday() >= 5:
                continue
            sample_students = random.sample(students_all, min(80, len(students_all)))
            for st in sample_students:
                status = random.choices(
                    ["present", "absent", "late", "excused"],
                    weights=[80, 10, 5, 5],
                )[0]
                db.add(AttendanceRecord(
                    school_id=school.id,
                    student_id=st.id,
                    class_id=st.class_id,
                    recorded_by=school_admin.id,
                    attendance_date=att_date,
                    status=status,
                ))

        # ── Assessments & Marks ──────────────────────────────────
        for klass in list(classes.values()):
            for subj in subject_list[:6]:  # first 6 subjects per class
                assessment = Assessment(
                    school_id=school.id,
                    subject_id=subj.id,
                    teacher_id=random.choice(teacher_list).id,
                    class_id=klass.id,
                    term_id=terms[1].id,
                    name=f"{subj.name} — Mid-Term Exam",
                    assessment_type="exam",
                    max_score=100,
                    weight=1.0,
                    date_administered=date(2026, 2, random.randint(10, 28)),
                )
                db.add(assessment)
                await db.flush()

                # Marks for each student in this class
                class_students = [
                    s for s in students_all if s.class_id == klass.id
                ]
                for st in class_students[:30]:
                    db.add(Mark(
                        school_id=school.id,
                        assessment_id=assessment.id,
                        student_id=st.id,
                        score=round(random.uniform(20, 98), 1),
                        remarks=None,
                    ))

        # ── Lesson Plans ─────────────────────────────────────────
        for tchr in teacher_list[:4]:
            for week in range(1, 6):
                for _ in range(3):
                    subj = random.choice(subject_list)
                    klass_obj = random.choice(list(classes.values()))
                    db.add(LessonPlan(
                        school_id=school.id,
                        teacher_id=tchr.id,
                        subject_id=subj.id,
                        class_id=klass_obj.id,
                        topic=f"{subj.name} Topic {week}.{random.randint(1,10)}",
                        objectives="Students will understand the core concepts.",
                        activities="Group discussion, practical exercises, and Q&A session.",
                        teaching_resources="Textbook, charts, whiteboard markers.",
                        assessment="Oral questions and written quiz at end of lesson.",
                        homework="Complete exercise in textbook, pages 45-47.",
                        completion_status=random.choice(["completed", "completed", "in_progress", "planned"]),
                        week_number=week,
                        term_number=1,
                    ))

        # ── Curriculum Assignment ────────────────────────────────
        cv_svc = CurriculumService(db)
        await cv_svc.seed_builtin_curricula()
        from app.models.curriculum import Curriculum as CurrModel
        kcse = await db.scalar(select(CurrModel).where(CurrModel.code == "844-KE"))
        if kcse:
            db.add(SchoolCurriculum(school_id=school.id, curriculum_id=kcse.id, is_active=True))
        await db.flush()
        print(f"📚 Curriculum: 8-4-4 (KCSE) assigned to {school.name}")

        # ── Workflows ─────────────────────────────────────────────
        wf_engine = WorkflowEngine(db, school.id)
        await wf_engine.ensure_builtin_workflows()
        await db.flush()
        print("🔄 Workflows: report card, exam, promotion, attendance lock")

        await db.commit()
        print("\n✅ 🌍 School Management System seed complete!\n")

        print("─" * 50)
        print("LOGIN CREDENTIALS")
        print("─" * 50)
        print("Platform Admin:  platform@example.com  / admin123")
        print("School Admin:    admin@example.com  / admin123")
        print("Teacher:         [any teacher email]        / teacher123")
        print("─" * 50)
        print("\n🌍 Curricula seeded: 6 (CBC, 8-4-4, Cambridge, IB, Nigeria, SA CAPS)")
        print("🔄 Workflows seeded: 4 (report cards, exams, promotion, attendance)")
        print("📡 Public API:       http://localhost:8000/public/v1/")
        print("   Auth: X-API-Key: demo-key-mombasa")
        print("─" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop all tables before seeding")
    args = parser.parse_args()
    asyncio.run(seed(reset=args.reset))
