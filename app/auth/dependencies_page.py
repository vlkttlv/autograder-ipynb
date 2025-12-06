from datetime import datetime
import logging
from fastapi.responses import RedirectResponse
import jwt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
# from jwt import PyJWKError
from app.auth.auth import create_access_token
from app.config import settings
from app.exceptions import (
    IncorrectRoleException,
    IncorrectTokenFormatException,
    TokenAbsentException,
    TokenExpiredException,
    UserIsNotPresentException,
)
from app.user.models import Users
from app.user.service import TokenService, UsersService
from app.db import async_session_maker, get_db_session
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


def get_token_page(request: Request):
    """Получение текущего токена из кук"""
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(
            url="/pages/auth/login",
        )
    return token


async def get_refresh_token_page(session: AsyncSession = Depends(get_db_session), token: str = Depends(get_token_page)):
    """Метод, получающий refresh токен"""
    try:
        payload = jwt.decode(
            token, options={"verify_signature": False, "verify_exp": False}
        )
    except Exception as e:
        # неверный формат токена
        return RedirectResponse(url="/pages/auth/login")

    user_id: str = payload.get("sub")
    if not user_id:
        return RedirectResponse(url="/pages/auth/login")

    refresh_user = await TokenService.find_one_or_none(session=session, user_id=int(user_id))
    if (
        not refresh_user
        or datetime.utcnow().timestamp() > refresh_user.expires_at.timestamp()
    ):
        # просрочен или не найден — редирект на логин
        return RedirectResponse(url="/pages/auth/login")

    return refresh_user.token


async def get_current_user_page(token: str = Depends(get_token_page)):
    """Возвращает текущего пользователя"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, settings.ALGORITHM)
    except Exception as e:
        # некорректный формат токена
        return RedirectResponse(url="/pages/auth/login")
    expire: str = payload.get("exp")
    if (not expire) or (int(expire) < datetime.utcnow().timestamp()):
        # срок действия токена истек
        return RedirectResponse(url="/pages/auth/login")
    user_id: str = payload.get("sub")
    if not user_id:
        # пользователя не существует
        # raise UserIsNotPresentException
        return RedirectResponse(url="/pages/auth/login")
    async with async_session_maker() as session:
        async with session.begin():
            user = await UsersService.find_one_or_none(session=session, id=int(user_id))
            if not user:
                # raise UserIsNotPresentException
                return RedirectResponse(url="/pages/auth/login")
            return user


async def get_role_page(current_user=Depends(get_current_user_page)):
    if current_user is not Users:
        return RedirectResponse(url="/pages/auth/login")
    return current_user.role


async def check_tutor_role_page(current_role=Depends(get_role_page)):
    if current_role == "STUDENT":
        return RedirectResponse(url="/pages/auth/login")
    return None


async def check_student_role_page(current_role=Depends(get_role_page)):
    if current_role == "TUTOR":
        return RedirectResponse(url="/pages/auth/login")
    return None


async def refresh_token_page(
    response: Response, refresh: str = Depends(get_refresh_token_page)
):
    """Обновление access токена с помощью refresh токена"""
    try:
        payload = jwt.decode(refresh, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
            # raise IncorrectTokenFormatException
            return RedirectResponse(url="/pages/auth/login")
    except Exception as e:
        # raise IncorrectTokenFormatException from e
        return RedirectResponse(url="/pages/auth/login")
    new_access_token = create_access_token({"sub": user_id, "role": role})
    response.set_cookie("access_token", new_access_token, httponly=True)
    logger.info(f"Токен был обновлен для юзера: {user_id} {role}")
    return {"access_token": new_access_token}
