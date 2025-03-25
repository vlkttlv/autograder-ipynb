from sqlalchemy import update
from app.service.base import BaseService
from app.user.models import RefreshToken, Users
from app.db import async_session_maker

class UsersService(BaseService):
    
    model = Users


class TokenService(BaseService):

    model = RefreshToken


    @classmethod
    async def update_token(cls, created_at, expires_at, user_id: int):
        """
        Обновляет refresh токен в БД

        -Аргументы:
            created_at: время создания токена
            expires_at: время истечения жизни токена
            user_id: индетификатор пользователя
            token: токен
        """
        async with async_session_maker() as session:
            stmt = update(cls.model).where(user_id==user_id).values(created_at=created_at, expires_at=expires_at)
            await session.execute(stmt)
            await session.commit()