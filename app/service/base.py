from sqlalchemy import delete, insert, select, update
from app.db import async_session_maker


class BaseService:

    """Базовый класс для работы с БД"""

    model = None

    @classmethod
    async def find_one_or_none(cls, **filter_by):
        """
        Находит и возвращает одну запись из таблицы в БД

        -Аргументы:
            **filter_by: атрибуты модели в качестве ключей и их значения в качестве значений.
        -Возвращает:
            Optional[cls.model]: Экземпляр модели, если запись найдена.
            Если запись не найдена, возвращается None.
        """
        async with async_session_maker() as session:
            stmt = select(cls.model).filter_by(**filter_by)
            res = await session.execute(stmt)
            return res.scalar_one_or_none()

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
            stmt = select(cls.model).filter_by(**filter_by)
            res = await session.execute(stmt)
            return res.scalars().all()

    @classmethod
    async def add(cls, **data):
        """
        Добавляет запись в таблицу БД

        -Аргументы:
            **data: атрибуты модели в качестве ключей и их значения в качестве значений.
        - Возвращает:
            MyModel
        """
        async with async_session_maker() as session:
            stmt = insert(cls.model).values(**data).returning(cls.model.id)
            res = await session.execute(stmt)
            await session.commit()
            return res.scalar()

    @classmethod
    async def delete(cls, **filter_by):
        """
        Удаляет запись из таблицы БД по соотвествующему условию

        -Аргументы:
        **filter_by: атрибуты модели в качестве ключей и их значения в качестве значений.
        """
        async with async_session_maker() as session:
            stmt = delete(cls.model).filter_by(**filter_by)
            await session.execute(stmt)
            await session.commit()

    @classmethod
    async def update(cls, model_id: int, **data):
        """
        Обновляет запись

        -Аргументы:
            model_id: ID записи, которую надо обновить
            **data: атрибуты модели в качестве ключей и их значения в качестве значений.
        """
        async with async_session_maker() as session:
            stmt = update(cls.model).where(cls.model.id == model_id).values(**data)
            await session.execute(stmt)
            await session.commit()