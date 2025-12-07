import jwt
import logging
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.services.dao_service import DisciplinesDAO
from app.db import get_db_session
from app.exceptions import (
    IncorrectEmailOrPasswordException,
    IncorrectTokenFormatException,
    UserAlreadyExistsException,
)
from app.user.models import Users
from app.user.schemas import (
    UserBaseSchema,
    UserRegisterSchema,
    UserResponseSchema,
    UserRole,
    UserTestRegisterSchemas,
)
from app.auth.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
)
from app.auth.dependencies import get_current_user, get_refresh_token
from app.user.service import GroupsService, TokenService, UsersService
from app.config import settings
from app.logger import configure_logging

router = APIRouter(prefix="/auth", tags=["Auth"])

configure_logging()
logger = logging.getLogger("users_service")


@router.post("/register", status_code=201, summary="Creates a new user")
async def register_user(user_data: UserRegisterSchema, session: AsyncSession = Depends(get_db_session)):
    """Регистрация пользователя"""
    existing_user = await UsersService.find_one_or_none(session=session, email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException

    hashed_password = get_password_hash(user_data.password)
    group_id = None

    if user_data.role == UserRole.STUDENT:
        find_group = await GroupsService.find_one_or_none(session=session, name=user_data.group)
        if not find_group:
            group_id = await GroupsService.add(session=session,name=user_data.group)
        else:
            group_id = find_group.id

    await UsersService.add(
        session=session,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        role=user_data.role,
        group_id=group_id,
    )
    logger.info("Пользователь зарегистрировался")
    return {"message": "Пользователь успешно зарегистрирован"}


@router.post(
    "/login", summary="Logs in a user and returns access and refresh tokens"
)
async def login_user(response: Response, user_data: UserBaseSchema, session: AsyncSession = Depends(get_db_session)):
    """Аутенфикация пользователя"""
    user = await authenticate_user(user_data.email, user_data.password, session)
    if not user:
        raise IncorrectEmailOrPasswordException

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = await create_refresh_token(
        {"sub": str(user.id), "role": user.role},
        session,
    )
    response.set_cookie("access_token", access_token, httponly=True)
    logger.info(f"Пользователь {user.email} залогинился")
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/logout", summary="Deletes tokens")
async def logout_user(
    response: Response, current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Выход из системы"""
    response.delete_cookie("access_token")
    await TokenService.delete(session=session, user_id=current_user.id)


@router.post("/test", summary="Creates the test users")
async def create_test_users():
    """Создание тестовых пользователей"""
    users_data = [
        UserTestRegisterSchemas(
            email="student@example.com",
            password="password",
            first_name="Студент",
            last_name="Тестовый",
            role=UserRole.STUDENT,
        ),
        UserTestRegisterSchemas(
            email="tutor@example.com",
            password="password",
            first_name="Преподаватель",
            last_name="Тестовый",
            role=UserRole.TUTOR,
        ),
        UserTestRegisterSchemas(
            email="admin@example.com",
            password="password",
            first_name="Администратор",
            last_name="Тестовый",
            role=UserRole.ADMIN,
        ),
    ]

    for user_data in users_data:
        hashed_password = get_password_hash(user_data.password)
        existing_user = await UsersService.find_one_or_none(
            session=session, email=user_data.email
        )
        if not existing_user:
            await UsersService.add(
                session=session,
                email=user_data.email,
                hashed_password=hashed_password,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                role=user_data.role,
            )
    logger.info("Были созданы тестовые пользователи")
    return {"message": "Тестовые пользователи успешно созданы"}


@router.post("/token/refresh", summary="Updates the access token")
async def refresh_token(
    response: Response, refresh: str = Depends(get_refresh_token)
):
    """Обновление access токена с помощью refresh токена"""
    try:
        payload = jwt.decode(refresh, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
            raise IncorrectTokenFormatException
    except Exception as e:
        raise IncorrectTokenFormatException from e
    new_access_token = create_access_token({"sub": user_id, "role": role})
    response.set_cookie("access_token", new_access_token, httponly=True)
    logger.info(f"Токен был обновлен для юзера: {user_id} {role}")
    return {"access_token": new_access_token}


@router.get(
    "/me",
    summary="Returns the info about user",
)
async def get_user(current_user: Users = Depends(get_current_user),
                   session: AsyncSession = Depends(get_db_session)):
    """Получение информации о пользователе"""
    data = await UsersService.get_full_user_info(session, current_user.id)

    return {
        "id": data["user"].id,
        "role": data["user"].role,
        "first_name": data["user"].first_name,
        "last_name": data["user"].last_name,
        "group": data["group"].name if data["group"] else None,
        "disciplines": [
            {"id": d.id, "name": d.name} for d in data["disciplines"]
        ],
    }