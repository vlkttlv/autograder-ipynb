from sqlalchemy import select, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.schemas import AssignmentUpdateSchema
from app.db import async_session_maker
from app.service.base import BaseService
from app.assignment.models import AssignmentFile, Assignments
from app.user.models import Disciplines


class AssignmentService(BaseService):
    model = Assignments

    @classmethod
    async def count(
        cls,
        session: AsyncSession | None = None,
        search: str | None = None,
        **filter_by,
    ) -> int:
        """
        Считает количество записей в таблице с учетом фильтров и поиска по name.
        """
        if session:
            stmt = select(func.count()).select_from(cls.model)
            if filter_by:
                stmt = stmt.filter_by(**filter_by)
            if search:
                stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))
            res = await session.execute(stmt)
            return res.scalar_one()
        else:
            async with async_session_maker() as new_session:
                stmt = select(func.count()).select_from(cls.model)
                if filter_by:
                    stmt = stmt.filter_by(**filter_by)
                if search:
                    stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))
                res = await new_session.execute(stmt)
                return res.scalar_one()

    @classmethod
    async def update_assignment(
        cls,
        model_id: str = None,
        updated_data: AssignmentUpdateSchema | None = None,
        session: AsyncSession | None = None,
    ):
        """
        Обновляет запись в БД в транзакции
        """
        if session:
            # В существующей транзакции
            if updated_data.name is not None:
                await cls.update(
                    session=session, model_id=model_id, name=updated_data.name
                )
            if updated_data.start_date is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    start_date=updated_data.start_date,
                )
            if updated_data.start_time is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    start_time=updated_data.start_time,
                )
            if updated_data.due_date is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    due_date=updated_data.due_date,
                )
            if updated_data.due_time is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    due_time=updated_data.due_time,
                )
            if updated_data.number_of_attempts is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    number_of_attempts=updated_data.number_of_attempts,
                )
            if updated_data.discipline_id is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    discipline_id=updated_data.discipline_id,
                )
            if updated_data.new_discipline_name is not None:
                await cls.update(
                    session=session,
                    model_id=model_id,
                    discipline_id=updated_data.new_discipline_name,
                )
        else:
            # Создаем новую транзакцию
            async with async_session_maker() as new_session:
                async with new_session.begin():
                    if updated_data.name is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            name=updated_data.name,
                        )
                    if updated_data.start_date is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            start_date=updated_data.start_date,
                        )
                    if updated_data.start_time is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            start_time=updated_data.start_time,
                        )
                    if updated_data.due_date is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            due_date=updated_data.due_date,
                        )
                    if updated_data.due_time is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            due_time=updated_data.due_time,
                        )
                    if updated_data.number_of_attempts is not None:
                        await cls.update(
                            session=new_session,
                            model_id=model_id,
                            number_of_attempts=updated_data.number_of_attempts,
                        )
                    if updated_data.discipline_id is not None:
                        await cls.update(
                            session=session,
                            model_id=model_id,
                            discipline_id=updated_data.discipline_id,
                        )
                    if updated_data.new_discipline_name is not None:
                        await cls.update(
                            session=session,
                            model_id=model_id,
                            discipline_id=updated_data.new_discipline_name,
                        )

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession | None = None,
        skip: int = 0,
        limit: int = 10,
        order_by: str | None = None,
        desc_order: bool = True,
        search: str | None = None,
        **filter_by,
    ):
        """
        Находит и возвращает несколько записей из таблицы БД, соответствующие условиям.
        """
        if session:
            # Используем переданную сессию
            stmt = select(cls.model)
            if filter_by:
                stmt = stmt.filter_by(**filter_by)
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
        else:
            # Создаем новую сессию
            async with async_session_maker() as new_session:
                stmt = select(cls.model)

                if filter_by:
                    stmt = stmt.filter_by(**filter_by)

                if search:
                    stmt = stmt.filter(cls.model.name.ilike(f"%{search}%"))

                if order_by:
                    column = getattr(cls.model, order_by)
                    stmt = stmt.order_by(
                        desc(column) if desc_order else asc(column),
                        desc(cls.model.id) if desc_order else asc(cls.model.id),
                    )

                stmt = stmt.offset(skip).limit(limit)

                res = await new_session.execute(stmt)
                return res.scalars().all()


class AssignmentFileService(BaseService):
    model = AssignmentFile

    @classmethod
    async def update_file(
        cls,
        session: AsyncSession | None = None,
        assignment_id: str = None,
        file_type: str = None,
        file_id: str = None,
        file_link: str = None,
    ):
        """
        Обновляет запись файла задания в БД.

        Args:
            session: Существующая сессия для транзакции
            assignment_id: ID задания
            file_type: Тип файла (ORIGINAL или MODIFIED)
            file_id: Новый file_id с Google dropbox
        """
        if session:
            # В существующей транзакции
            # Ищем существующую запись
            existing = await cls.find_one_or_none(
                session=session,
                assignment_id=assignment_id,
                file_type=file_type,
            )

            if existing:
                # Обновляем file_id
                await cls.update(
                    session=session, model_id=existing.id, file_id=file_id
                )
            else:
                # Создаем новую запись
                await cls.add(
                    session=session,
                    assignment_id=assignment_id,
                    file_type=file_type,
                    file_id=file_id,
                    file_link=file_link,
                )
        else:
            # Создаем новую транзакцию
            async with async_session_maker() as new_session:
                async with new_session.begin():
                    # Ищем существующую запись
                    existing = await cls.find_one_or_none(
                        session=new_session,
                        assignment_id=assignment_id,
                        file_type=file_type,
                    )

                    if existing:
                        # Обновляем file_id
                        await cls.update(
                            session=new_session,
                            model_id=existing.id,
                            file_id=file_id,
                            file_link=file_link,
                        )
                    else:
                        # Создаем новую запись
                        await cls.add(
                            session=new_session,
                            assignment_id=assignment_id,
                            file_type=file_type,
                            file_id=file_id,
                        )

    @classmethod
    async def update_or_create(
        cls,
        session: AsyncSession,
        assignment_id: str,
        file_type: str,
        file_id: str,
        file_link: str,
    ):
        """Обновление существующей записи или создание новой"""

        record = await cls.find_one_or_none(
            session=session,
            assignment_id=assignment_id,
            file_type=file_type,
        )

        if record:
            record.file_id = file_id
            record.file_link = file_link
            session.add(record)  # обязательно добавить в сессию
        else:
            await cls.add(
                session=session,
                assignment_id=assignment_id,
                file_type=file_type,
                file_id=file_id,
                file_link=file_link,
            )


class DisciplinesService(BaseService):
    model = Disciplines
