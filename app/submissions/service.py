from sqlalchemy.orm import selectinload
from sqlalchemy import select, func
from app.service.base import BaseService
from app.submissions.models import Submissions, SubmissionFiles
from app.db import async_session_maker

class SubmissionsService(BaseService):

    model = Submissions

    @classmethod
    async def find_all(cls, **filter_by):
        """
        Находит и возвращает несколько записей из таблицы БД, соответствующие условиям

        -Аргументы:
            **filter_by: атрибуты модели в качестве ключей и их значения в качестве значений.
        -Пример:
            await Users.find_all(name='John', age=30)
            Вернет все записи, где name равно 'John' и age равно 30.
        -Возвращает:
            List[cls.model]: Список экземпляров модели, удовлетворяющих условиям фильтрации.
            Если записи не найдены, возвращается пустой список.
        """
        async with async_session_maker() as session:
            stmt = select(cls.model).options(selectinload(Submissions.assignment)).filter_by(**filter_by)
            res = await session.execute(stmt)
            return res.scalars().all()
        


    @classmethod
    async def get_statistics(cls, assignment_id: int):
        async with async_session_maker() as session:
            # stmt = select(cls.model).options(selectinload(Submissions.user)).where(cls.model.assignment_id == assignment_id)
            # res = await session.execute(stmt)
            # return res.scalars().all()

            # получаем список решений
            stmt = (
                select(cls.model)
                .options(selectinload(Submissions.user))
                .where(cls.model.assignment_id == assignment_id)
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
        

class SubmissionFilesService(BaseService):

    model = SubmissionFiles
