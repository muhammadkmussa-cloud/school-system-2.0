"""Teacher management routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin, Pagination
from app.core.security import hash_password
from app.models.teacher import Teacher
from app.models.user import LoginHistory, PasswordHistory, User
from app.schemas.teacher import (
    TeacherCreate,
    TeacherList,
    TeacherOut,
    TeacherUpdate,
    BulkTeacherCreate,
    BulkTeacherCreateResult,
    TeacherCredentials,
    TeacherResetPasswordResult,
)
from app.services.audit_service import log_account_event

router = APIRouter()


@router.get("", response_model=TeacherList)
async def list_teachers(
    db: DB,
    current_user: RequireSchoolAdmin,
    pagination: Pagination = Depends(),
    search: str = "",
):
    base = select(Teacher).where(Teacher.school_id == current_user.school_id)
    count_q = select(func.count(Teacher.id)).where(
        Teacher.school_id == current_user.school_id
    )

    if search:
        ilike = f"%{search}%"
        base = base.where(
            (Teacher.full_name.ilike(ilike)) | (Teacher.email.ilike(ilike))
        )
        count_q = count_q.where(
            (Teacher.full_name.ilike(ilike)) | (Teacher.email.ilike(ilike))
        )

    total = await db.scalar(count_q)
    rows = (
        await db.scalars(
            base.order_by(Teacher.full_name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()

    result = []
    for r in rows:
        out = TeacherOut.model_validate(r)
        if r.user_id:
            user = await db.scalar(select(User).where(User.id == r.user_id))
            if user:
                out.user_status = user.status
                out.must_change_password = user.must_change_password
        result.append(out)

    return TeacherList(
        items=result,
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    payload: TeacherCreate, db: DB, current_user: RequireSchoolAdmin
):
    existing_user = await db.scalar(select(User).where(User.email == payload.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    password = payload.password or uuid.uuid4().hex[:12]
    username = f"teacher.{payload.employee_number.lower()}"

    user = User(
        school_id=current_user.school_id,
        username=username,
        email=payload.email,
        hashed_password=hash_password(password),
        full_name=payload.full_name,
        role="teacher",
        phone=payload.phone,
        status="pending_first_login",
        must_change_password=True,
    )
    db.add(user)
    await db.flush()

    teacher = Teacher(
        school_id=current_user.school_id,
        user_id=user.id,
        employee_number=payload.employee_number,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
    )
    teacher.is_active = False
    db.add(teacher)
    await db.flush()
    await db.refresh(teacher)

    out = TeacherOut.model_validate(teacher)
    out.user_status = user.status
    out.must_change_password = user.must_change_password
    return out


@router.post("/bulk", response_model=BulkTeacherCreateResult, status_code=status.HTTP_201_CREATED)
async def bulk_create_teachers(
    payload: BulkTeacherCreate, db: DB, current_user: RequireSchoolAdmin
):
    if payload.count < 1:
        raise HTTPException(status_code=400, detail="count must be at least 1")
    if payload.count > settings.MAX_TEACHERS_PER_SCHOOL:
        raise HTTPException(
            status_code=400,
            detail=f"count cannot exceed {settings.MAX_TEACHERS_PER_SCHOOL}",
        )

    # Check existing teacher count
    existing = await db.scalar(
        select(func.count(Teacher.id)).where(Teacher.school_id == current_user.school_id)
    )
    if existing and existing + payload.count > settings.MAX_TEACHERS_PER_SCHOOL:
        raise HTTPException(
            status_code=400,
            detail=f"Total teachers would exceed limit of {settings.MAX_TEACHERS_PER_SCHOOL}",
        )

    # Get school code for generating temp usernames
    from app.models.school import School
    school = await db.scalar(
        select(School).where(School.id == current_user.school_id)
    )
    school_code = school.code.lower() if school else "sch"

    # Fetch existing teacher count for numbering
    teacher_count = existing or 0
    created = []
    for i in range(payload.count):
        num = teacher_count + i + 1
        emp_number = f"TCH{num:04d}"
        username = f"teacher.{emp_number.lower()}"
        temp_email = f"{username}@{school_code}.temp.example.com"
        temp_password = uuid.uuid4().hex[:12]

        user = User(
            school_id=current_user.school_id,
            username=username,
            email=temp_email,
            hashed_password=hash_password(temp_password),
            full_name=f"Teacher {num:04d}",
            role="teacher",
            status="pending_first_login",
            must_change_password=True,
        )
        db.add(user)
        await db.flush()

        teacher = Teacher(
            school_id=current_user.school_id,
            user_id=user.id,
            employee_number=emp_number,
            full_name=f"Teacher {num:04d}",
            email=temp_email,
        )
        teacher.is_active = False  # pending activation
        db.add(teacher)
        await db.flush()

        created.append(TeacherCredentials(
            id=teacher.id,
            employee_number=emp_number,
            full_name=f"Teacher {num:04d}",
            email=temp_email,
            temp_password=temp_password,
            is_active=False,
        ))

    return BulkTeacherCreateResult(created=payload.count, teachers=created)


@router.get("/credentials", response_model=list[TeacherCredentials])
async def list_teacher_credentials(
    db: DB, current_user: RequireSchoolAdmin
):
    teachers = await db.scalars(
        select(Teacher).where(Teacher.school_id == current_user.school_id)
        .order_by(Teacher.employee_number)
    )
    result = []
    for teacher in teachers.all():
        temp_password = "********"  # masked in production
        if not teacher.is_active:
            temp_password = uuid.uuid4().hex[:12]
            user = await db.scalar(select(User).where(User.id == teacher.user_id))
            if user:
                user.hashed_password = hash_password(temp_password)
                await db.flush()
        result.append(TeacherCredentials(
            id=teacher.id,
            employee_number=teacher.employee_number,
            full_name=teacher.full_name,
            email=teacher.email,
            temp_password=temp_password,
            is_active=teacher.is_active,
        ))
    return result


@router.post("/{teacher_id}/reset-password", response_model=TeacherResetPasswordResult)
async def reset_teacher_password(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    new_password = uuid.uuid4().hex[:12]
    user.hashed_password = hash_password(new_password)
    user.refresh_token_jti = None
    await db.flush()

    return TeacherResetPasswordResult(
        new_password=new_password,
        teacher_id=teacher.id,
    )


@router.get("/{teacher_id}", response_model=TeacherOut)
async def get_teacher(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    out = TeacherOut.model_validate(teacher)
    if teacher.user_id:
        user = await db.scalar(select(User).where(User.id == teacher.user_id))
        if user:
            out.user_status = user.status
            out.must_change_password = user.must_change_password
    return out


@router.patch("/{teacher_id}", response_model=TeacherOut)
async def update_teacher(
    teacher_id: uuid.UUID,
    payload: TeacherUpdate,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(teacher, field, value)
    await db.flush()
    await db.refresh(teacher)
    out = TeacherOut.model_validate(teacher)
    if teacher.user_id:
        user = await db.scalar(select(User).where(User.id == teacher.user_id))
        if user:
            out.user_status = user.status
            out.must_change_password = user.must_change_password
    return out


@router.post("/{teacher_id}/toggle-active", response_model=TeacherOut)
async def toggle_teacher_active(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    teacher.is_active = not teacher.is_active
    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if user:
        user.is_active = teacher.is_active
        user.status = "active" if teacher.is_active else "disabled"
        await log_account_event(
            db, current_user.school_id, current_user.id, current_user.role, current_user.full_name,
            "account_enabled" if teacher.is_active else "account_disabled",
            str(user.id), user.email,
        )
    await db.flush()
    await db.refresh(teacher)
    out = TeacherOut.model_validate(teacher)
    if teacher.user_id:
        user = await db.scalar(select(User).where(User.id == teacher.user_id))
        if user:
            out.user_status = user.status
            out.must_change_password = user.must_change_password
    return out


@router.post("/{teacher_id}/lock", response_model=dict)
async def lock_teacher_account(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    user.status = "locked"
    user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
    await log_account_event(
        db, current_user.school_id, current_user.id, current_user.role, current_user.full_name,
        "account_locked", str(user.id), user.email,
    )
    await db.flush()
    return {"status": "locked", "teacher_id": str(teacher_id)}


@router.post("/{teacher_id}/unlock", response_model=dict)
async def unlock_teacher_account(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    user.status = "active"
    user.locked_until = None
    user.failed_login_attempts = 0
    await log_account_event(
        db, current_user.school_id, current_user.id, current_user.role, current_user.full_name,
        "account_unlocked", str(user.id), user.email,
    )
    await db.flush()
    return {"status": "unlocked", "teacher_id": str(teacher_id)}


@router.post("/{teacher_id}/force-reset", response_model=dict)
async def force_reset_teacher_password(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    new_password = uuid.uuid4().hex[:12]
    user.hashed_password = hash_password(new_password)
    user.must_change_password = True
    user.refresh_token_jti = None
    await log_account_event(
        db, current_user.school_id, current_user.id, current_user.role, current_user.full_name,
        "password_reset_by_admin", str(user.id), user.email,
    )
    await db.flush()
    return {"new_password": new_password, "teacher_id": str(teacher_id), "must_change_password": True}


@router.get("/{teacher_id}/account-status", response_model=dict)
async def get_teacher_account_status(
    teacher_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    teacher = await db.scalar(
        select(Teacher).where(
            Teacher.id == teacher_id,
            Teacher.school_id == current_user.school_id,
        )
    )
    if not teacher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    user = await db.scalar(select(User).where(User.id == teacher.user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")

    # Get last 5 login attempts
    login_attempts = await db.scalars(
        select(LoginHistory).where(LoginHistory.user_id == user.id)
        .order_by(LoginHistory.attempted_at.desc())
        .limit(5)
    )

    # Get password reset history
    pwd_resets = await db.scalars(
        select(PasswordHistory).where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
    )

    return {
        "user_id": str(user.id),
        "teacher_id": str(teacher.id),
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "must_change_password": user.must_change_password,
        "terms_accepted": user.terms_accepted,
        "profile_completed": user.profile_completed,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "failed_login_attempts": user.failed_login_attempts,
        "password_changed_at": user.password_changed_at.isoformat() if user.password_changed_at else None,
        "recent_login_attempts": [
            {
                "success": l.success,
                "ip_address": l.ip_address,
                "attempted_at": l.attempted_at.isoformat() if l.attempted_at else None,
            }
            for l in login_attempts
        ],
        "password_history_count": len(pwd_resets.all()),
    }
