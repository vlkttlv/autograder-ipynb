from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.service.base import BaseDAO
from app.user.models import Disciplines, RefreshToken, Users, Groups
from app.db import async_session_maker


class UsersService(BaseDAO):
    model = Users

    @classmethod
    async def get_full_user_info(cls, session: AsyncSession, user_id: int):
        q_user = await session.execute(
            select(cls.model).where(cls.model.id == user_id)
        )
        user = q_user.scalar_one_or_none()

        if not user:
            return None

        group = None
        disciplines = []

        if user.role == "STUDENT":
            if user.group_id:
                q_group = await session.execute(
                    select(Groups).where(Groups.id == user.group_id)
                )
                group = q_group.scalar_one_or_none()

        if user.role == "TUTOR":
            q_disc = await session.execute(
                select(Disciplines).where(Disciplines.teacher_id == user.id)
            )
            disciplines = q_disc.scalars().all()

        return {
            "user": user,
            "group": group,
            "disciplines": disciplines,
        }


class GroupsService(BaseDAO):
    model = Groups


class TokenService(BaseDAO):
    model = RefreshToken

    @classmethod
    async def update_token(cls, created_at, expires_at, token, user_id: int):
        """
        Обновляет refresh токен в БД

        -Аргументы:
            created_at: время создания токена
            expires_at: время истечения жизни токена
            user_id: индетификатор пользователя
            token: токен
        """
        async with async_session_maker() as session:
            stmt = (
                update(cls.model)
                .where(cls.model.user_id == user_id)
                .values(
                    created_at=created_at, expires_at=expires_at, token=token
                )
            )
            await session.execute(stmt)
            await session.commit()
