from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from app.db import async_session_maker


class BaseDAO:
    """Базовый класс для работы с БД"""

    model = None

    @classmethod
    async def find_one_or_none(
        cls, session: AsyncSession, **filter_by
    ) -> Optional[Any]:
        """
        Находит и возвращает одну запись из таблицы в БД

        Args:
            session: Существующая сессия для работы в транзакции
            **filter_by: Атрибуты модели для фильтрации

        Returns:
            Optional[cls.model]: Экземпляр модели или None
        """
        # Используем переданную сессию
        stmt = select(cls.model).filter_by(**filter_by)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def find_all(
        cls, session: AsyncSession, **filter_by
    ) -> List[Any]:
        """
        Находит и возвращает несколько записей из таблицы БД

        Args:
            session: Существующая сессия для работы в транзакции
            **filter_by: Атрибуты модели для фильтрации

        Returns:
            List[cls.model]: Список экземпляров модели
        """
        stmt = select(cls.model).filter_by(**filter_by)
        res = await session.execute(stmt)
        return res.scalars().all()

    @classmethod
    async def add(cls, session: AsyncSession, **data) -> Any:
        """
        Добавляет запись в таблицу БД

        Args:
            session: Существующая сессия для работы в транзакции
            **data: Данные для создания записи

        Returns:
            ID созданной записи
        """
        stmt = insert(cls.model).values(**data).returning(cls.model.id)
        res = await session.execute(stmt)
        return res.scalar()

    @classmethod
    async def delete(
        cls, session: AsyncSession, **filter_by
    ) -> None:
        """
        Удаляет запись из таблицы БД

        Args:
            session: Существующая сессия для работы в транзакции
            **filter_by: Условия для удаления
        """
        stmt = delete(cls.model).filter_by(**filter_by)
        await session.execute(stmt)


    @classmethod
    async def update(
        cls, session: AsyncSession, model_id: int, **data
    ) -> None:
        """
        Обновляет запись в таблице БД

        Args:
            model_id: ID записи для обновления
            session: Существующая сессия для работы в транзакции
            **data: Данные для обновления
        """
        stmt = (
            update(cls.model).where(cls.model.id == model_id).values(**data)
        )
        await session.execute(stmt)

    @classmethod
    async def count(
        cls, session: AsyncSession, **filter_by
    ) -> int:
        """
        Подсчитывает количество записей, удовлетворяющих условиям

        Args:
            session: Существующая сессия для работы в транзакции
            **filter_by: Условия для подсчета

        Returns:
            int: Количество записей
        """
        stmt = select(cls.model).filter_by(**filter_by)
        res = await session.execute(
            select(cls.model.id).select_from(stmt.subquery())
        )
        return len(res.all())
