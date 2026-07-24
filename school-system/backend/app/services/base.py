"""School Management System — Base repository with multi-tenancy enforcement.

Every query is automatically filtered by school_id unless the caller
is a platform_admin (who operates across all schools).
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta

from app.core.dependencies import Pagination

ModelType = TypeVar("ModelType", bound=DeclarativeMeta)


class BaseRepository(Generic[ModelType]):
    """CRUD base with school-isolation built in.

    Usage::

        repo = BaseRepository(Student, db, school_id="abc-123", user_role="school_admin")
        students = await repo.list(page=1, page_size=20)
    """

    def __init__(
        self,
        model: type[ModelType],
        db: AsyncSession,
        *,
        school_id: uuid.UUID | str | None = None,
        user_role: str = "",
    ):
        self.model = model
        self.db = db
        self.school_id = str(school_id) if school_id else None
        self.is_platform = user_role == "platform_admin"

    # ── helpers ──────────────────────────────────────────────────

    def _has_column(self, name: str) -> bool:
        return hasattr(self.model, name)

    def _base_select(self):
        stmt = select(self.model)
        if self._has_column("school_id") and not self.is_platform and self.school_id:
            stmt = stmt.where(getattr(self.model, "school_id") == self.school_id)
        return stmt

    def _count_select(self):
        stmt = select(func.count(self.model.id))
        if self._has_column("school_id") and not self.is_platform and self.school_id:
            stmt = stmt.where(getattr(self.model, "school_id") == self.school_id)
        return stmt

    # ── CRUD ─────────────────────────────────────────────────────

    async def list(
        self,
        *filters: Any,
        page: int = 1,
        page_size: int = 20,
        order_by: Any = None,
    ) -> tuple[list[ModelType], int]:
        stmt = self._base_select()
        count_q = self._count_select()

        for f in filters:
            stmt = stmt.where(f)
            count_q = count_q.where(f)

        if order_by is not None:
            stmt = stmt.order_by(order_by)

        total = await self.db.scalar(count_q)
        offset = (page - 1) * page_size
        rows = (await self.db.scalars(stmt.offset(offset).limit(page_size))).all()
        return rows, total or 0

    async def get(self, id: uuid.UUID | str) -> ModelType | None:
        stmt = self._base_select().where(self.model.id == id)
        return await self.db.scalar(stmt)

    async def create(self, **kwargs: Any) -> ModelType:
        if self._has_column("school_id") and "school_id" not in kwargs and self.school_id:
            kwargs["school_id"] = self.school_id
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def update(self, instance: ModelType, **kwargs: Any) -> ModelType:
        for field, value in kwargs.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()

    async def count(self, *filters: Any) -> int:
        q = self._count_select()
        for f in filters:
            q = q.where(f)
        return await self.db.scalar(q) or 0
