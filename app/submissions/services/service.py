from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import desc, select, func
from app.assignment.models import Assignments
from app.service.base import BaseService
from app.submissions.models import Submissions, SubmissionFiles
from app.db import async_session_maker

class SubmissionsService(BaseService):

    model = Submissions

    @classmethod
    async def find_all(
        cls,
        user_id: int,
        skip: int = 0,
        limit: int = 10,
        order: str = "desc",
        search: str | None = None,
    ):
        async with async_session_maker() as session:
            query = (
                select(Submissions)
                .options(joinedload(Submissions.assignment))
                .where(Submissions.user_id == user_id)
            )

            if search:
                query = query.join(Submissions.assignment).where(
                    Assignments.name.ilike(f"%{search}%")
                )

            if order == "desc":
                query = query.order_by(desc(Submissions.created_at))
            else:
                query = query.order_by(Submissions.created_at)

            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()
        

    @classmethod
    async def get_statistics(cls, assignment_id: int, skip: int = 0, limit: int = 10):
        async with async_session_maker() as session:

            # получаем список решений
            stmt = (
                select(cls.model)
                .options(selectinload(Submissions.user))
                .where(cls.model.assignment_id == assignment_id)
                .offset(skip)
                .limit(limit)
            )

            res = await session.execute(stmt)
            submissions = res.scalars().all()

            # cчитаем средний балл
            avg_stmt = select(func.avg(cls.model.score)).where(cls.model.assignment_id == assignment_id)
            avg_res = await session.execute(avg_stmt)
            avg_score = avg_res.scalar()

            return {
                "submissions": submissions,
                "average_score": float(avg_score) if avg_score is not None else 0
            }
        
    @classmethod
    async def count(cls, search: str | None = None, **filter_by):
        async with async_session_maker() as new_session:
            stmt = select(func.count()).select_from(cls.model)
            if filter_by:
                stmt = stmt.filter_by(**filter_by)
            if search:
                stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))
            res = await new_session.execute(stmt)
            return res.scalar_one()

        
class SubmissionFilesService(BaseService):

    model = SubmissionFiles
