from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, func, asc, or_
from app.assignment.models import Assignments
from app.service.base import BaseDAO
from app.submissions.models import Submissions, SubmissionFiles
from app.db import async_session_maker
from app.user.models import Users


class SubmissionsDAO(BaseDAO):
    model = Submissions

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        order_by: str | None = None,
        desc_order: bool = True,
        search: str | None = None,
        discipline_id: int | None = None
    ):
        query = (
            select(Submissions)
            .join(Submissions.assignment)
            .options(joinedload(Submissions.assignment))
            .where(Submissions.user_id == user_id)
        )

        if discipline_id is not None:
            query = query.where(Assignments.discipline_id == discipline_id)

        if search:
            query = query.where(Assignments.name.ilike(f"%{search}%"))

        if order_by:
            column = getattr(Submissions, order_by)
            query = query.order_by(desc(column) if desc_order else asc(column))

        query = query.offset(skip).limit(limit)

        result = await session.execute(query)
        return result.scalars().all()


    @classmethod
    async def get_statistics(
        cls,
        session: AsyncSession,
        assignment_id: int,
        skip: int = 0,
        limit: int = 10,
        order_by: str | None = None,
        desc_order: bool = True,
        search: str | None = None,
    ):
        stmt = (
            select(cls.model)
            .join(Submissions.user)
            .options(selectinload(Submissions.user))
            .where(cls.model.assignment_id == assignment_id)
        )

        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Users.first_name).like(pattern),
                    func.lower(Users.last_name).like(pattern),
                )
            )

        if order_by:
            column = getattr(cls.model, order_by)
            stmt = stmt.order_by(desc(column) if desc_order else asc(column))

        stmt = stmt.offset(skip).limit(limit)
        res = await session.execute(stmt)
        submissions = res.scalars().all()

        # средний балл
        avg_stmt = select(func.avg(cls.model.score)).where(
            cls.model.assignment_id == assignment_id
        )
        avg_res = await session.execute(avg_stmt)
        avg_score = avg_res.scalar()

        return {
            "submissions": submissions,
            "average_score": float(avg_score) if avg_score is not None else 0,
        }

    @classmethod
    async def count(
        cls,
        session: AsyncSession,
        search: str | None = None,
        discipline_id: int | None = None,
        **filter_by
    ):
        stmt = (
            select(func.count(Submissions.id))
            .select_from(Submissions)
            .join(Submissions.assignment)
        )

        for key, value in filter_by.items():
            column = getattr(Submissions, key)
            stmt = stmt.where(column == value)

        if discipline_id is not None:
            stmt = stmt.where(Assignments.discipline_id == discipline_id)

        if search:
            stmt = stmt.where(Assignments.name.ilike(f"%{search}%"))

        result = await session.execute(stmt)
        return result.scalar()



class SubmissionFilesDAO(BaseDAO):
    model = SubmissionFiles
