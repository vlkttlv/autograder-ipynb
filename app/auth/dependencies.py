from datetime import datetime
from fastapi.responses import RedirectResponse
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, Request
from app.db import async_session_maker
# from jwt import PyJWKError
from app.config import settings
from app.db import get_db_session
from app.exceptions import (
    IncorrectRoleException,
    IncorrectTokenFormatException,
    TokenAbsentException,
    TokenExpiredException,
    UserIsNotPresentException,
)
from app.user.service import TokenService, UsersService


def get_token(request: Request):
    """Получение текущего токена из кук"""
    token = request.cookies.get("access_token")
    if not token:
        raise TokenAbsentException
    return token


async def get_refresh_token(token: str = Depends(get_token),
                            session: AsyncSession = Depends(get_db_session),):
    """Метод, получающий refresh токен"""
    # декодируем текущий access токен без проверки подписи и времени
    try:
        payload = jwt.decode(
            token, options={"verify_signature": False, "verify_exp": False}
        )
    except Exception as e:
        raise IncorrectTokenFormatException from e
    user_id: str = payload.get("sub")
    if not user_id:
        raise UserIsNotPresentException
    # находим refresh токен для текущего пользователя
    refresh_user = await TokenService.find_one_or_none(session=session, user_id=int(user_id))
    # если refresh токен просрочен, то выбрасываем исключение
    if datetime.utcnow().timestamp() > refresh_user.expires_at.timestamp():
        raise HTTPException(status_code=401)
    refresh_token = refresh_user.token
    return refresh_token


async def get_current_user(token: str = Depends(get_token),):
    """Возвращает текущего пользователя"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
    except Exception as e:
        raise IncorrectTokenFormatException from e
    expire: str = payload.get("exp")
    if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
        raise TokenExpiredException
    user_id: str = payload.get("sub")
    if not user_id:
        raise UserIsNotPresentException
    async with async_session_maker() as session:
        async with session.begin():
            user = await UsersService.find_one_or_none(session=session, id=int(user_id))
            if not user:
                raise UserIsNotPresentException
            return user


async def get_role(current_user=Depends(get_current_user)):
    return current_user.role


async def check_tutor_role(current_role=Depends(get_role)):
    if current_role == "STUDENT":
        raise IncorrectRoleException


async def check_student_role(current_role=Depends(get_role)):
    if current_role == "TUTOR":
        raise IncorrectRoleException
