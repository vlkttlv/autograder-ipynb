from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.schemas import AssignmentUpdateSchema
from app.db import async_session_maker
from app.service.base import BaseDAO
from app.assignment.models import AssignmentFile, Assignments
from app.submissions.models import Submissions
from app.user.models import Disciplines


class AssignmentDAO(BaseDAO):

    model = Assignments

    @classmethod
    async def count(
        cls,
        session: AsyncSession,
        search: str | None = None,
        **filter_by,
    ) -> int:
        """
        Считает количество записей в таблице с учетом фильтров и поиска по name.
        """
        stmt = select(func.count()).select_from(cls.model)

        if filter_by:
            stmt = stmt.filter_by(**filter_by)

        if search:
            stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))
        
        res = await session.execute(stmt)
        return res.scalar_one()


    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        order_by: str | None = None,
        desc_order: bool = True,
        search: str | None = None,
        user_id: int | None = None,
        discipline_id: int | None = None,
    ):
        """
        Находит и возвращает несколько записей из таблицы БД, соответствующие условиям.
        """
        stmt = select(cls.model)

        if user_id is not None:
            stmt = stmt.filter(cls.model.user_id == user_id)

        if discipline_id is not None:
            stmt = stmt.filter(cls.model.discipline_id == discipline_id)

        if search:
            stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))

        if order_by:
            column = getattr(cls.model, order_by)
            stmt = stmt.order_by(
                desc(column) if desc_order else asc(column),
                desc(cls.model.id) if desc_order else asc(cls.model.id),
            )
            
        stmt = stmt.offset(skip).limit(limit)

        res = await session.execute(stmt)
        return res.scalars().all()


class AssignmentFileDAO(BaseDAO):
    model = AssignmentFile

    @classmethod
    async def update_or_create(
        cls,
        session: AsyncSession,
        assignment_id: str = None,
        file_type: str = None,
        file_id: str = None,
        file_link: str = None,
    ):
        """
        Обновляет существующую запись файла или создаёт новую.

        Args:
            session: Существующая сессия для транзакции
            assignment_id: ID задания
            file_type: Тип файла (ORIGINAL или MODIFIED)
            file_id: Новый file_id с dropbox
        """
        # Ищем существующую запись
        existing = await cls.find_one_or_none(
            session=session,
            assignment_id=assignment_id,
            file_type=file_type,
        )


        update_fields = {k: v for k, v in {
            "file_id": file_id,
            "file_link": file_link
        }.items() if v is not None}

        if existing:
            if update_fields:
                await cls.update(session=session, model_id=existing.id, **update_fields)
        else:
            await cls.add(
                session=session,
                assignment_id=assignment_id,
                file_type=file_type,
                **update_fields
            )


class DisciplinesDAO(BaseDAO):
    model = Disciplines

    @classmethod
    async def find_for_student(cls, session: AsyncSession, student_id: int):
        query = (
            select(cls.model)
            .join(Assignments, Assignments.discipline_id == Disciplines.id)
            .join(Submissions, Submissions.assignment_id == Assignments.id)
            .where(Submissions.user_id == student_id)
            .group_by(cls.model.id)
        )
        result = await session.execute(query)
        return result.scalars().all()
