from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Any
from app.db import async_session_maker


class BaseService:
    """Базовый класс для работы с БД с поддержкой транзакций"""

    model = None

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession | None = None, **filter_by) -> Optional[Any]:
        """
        Находит и возвращает одну запись из таблицы в БД
        
        Args:
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **filter_by: Атрибуты модели для фильтрации
            
        Returns:
            Optional[cls.model]: Экземпляр модели или None
        """
        if session:
            # Используем переданную сессию
            stmt = select(cls.model).filter_by(**filter_by)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()
        else:
            # Создаем новую сессию
            async with async_session_maker() as new_session:
                stmt = select(cls.model).filter_by(**filter_by)
                res = await new_session.execute(stmt)
                return res.scalar_one_or_none()

    @classmethod
    async def find_all(cls, session: AsyncSession | None = None, **filter_by) -> List[Any]:
        """
        Находит и возвращает несколько записей из таблицы БД
        
        Args:
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **filter_by: Атрибуты модели для фильтрации
            
        Returns:
            List[cls.model]: Список экземпляров модели
        """
        if session:
            stmt = select(cls.model).filter_by(**filter_by)
            res = await session.execute(stmt)
            return res.scalars().all()
        else:
            async with async_session_maker() as new_session:
                stmt = select(cls.model).filter_by(**filter_by)
                res = await new_session.execute(stmt)
                return res.scalars().all()

    @classmethod
    async def add(cls, session: AsyncSession | None = None, **data) -> Any:
        """
        Добавляет запись в таблицу БД
        
        Args:
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **data: Данные для создания записи
            
        Returns:
            ID созданной записи
        """
        if session:
            stmt = insert(cls.model).values(**data).returning(cls.model.id)
            res = await session.execute(stmt)
            return res.scalar()
        else:
            async with async_session_maker() as new_session:
                async with new_session.begin():
                    stmt = insert(cls.model).values(**data).returning(cls.model.id)
                    res = await new_session.execute(stmt)
                    return res.scalar()

    @classmethod
    async def delete(cls, session: AsyncSession | None = None, **filter_by) -> None:
        """
        Удаляет запись из таблицы БД
        
        Args:
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **filter_by: Условия для удаления
        """
        if session:
            stmt = delete(cls.model).filter_by(**filter_by)
            await session.execute(stmt)
        else:
            async with async_session_maker() as new_session:
                async with new_session.begin():
                    stmt = delete(cls.model).filter_by(**filter_by)
                    await new_session.execute(stmt)

    @classmethod
    async def update(cls, model_id: int, session: AsyncSession | None = None, **data) -> None:
        """
        Обновляет запись в таблице БД
        
        Args:
            model_id: ID записи для обновления
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **data: Данные для обновления
        """
        if session:
            stmt = update(cls.model).where(cls.model.id == model_id).values(**data)
            await session.execute(stmt)
        else:
            async with async_session_maker() as new_session:
                async with new_session.begin():
                    stmt = update(cls.model).where(cls.model.id == model_id).values(**data)
                    await new_session.execute(stmt)

    @classmethod
    async def count(cls, session: AsyncSession | None = None, **filter_by) -> int:
        """
        Подсчитывает количество записей, удовлетворяющих условиям
        
        Args:
            session: Существующая сессия для работы в транзакции. Если None - создается новая.
            **filter_by: Условия для подсчета
            
        Returns:
            int: Количество записей
        """
        if session:
            stmt = select(cls.model).filter_by(**filter_by)
            res = await session.execute(select(cls.model.id).select_from(stmt.subquery()))
            return len(res.all())
        else:
            async with async_session_maker() as new_session:
                stmt = select(cls.model).filter_by(**filter_by)
                res = await new_session.execute(select(cls.model.id).select_from(stmt.subquery()))
                return len(res.all())
