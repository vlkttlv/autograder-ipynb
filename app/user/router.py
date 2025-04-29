import logging
from fastapi import APIRouter, Depends, Response
import jwt
from jwt.exceptions import InvalidKeyError
from app.exceptions import (IncorrectEmailOrPasswordException,
                            IncorrectTokenFormatException,
                            UserAlreadyExistsException)
from app.user.models import Users
from app.user.schemas import (UserBaseSchema,
                              UserRegisterSchema,
                              UserResponseSchema,
                              UserRole, UserTestRegisterSchemas)
from app.auth.auth import (authenticate_user,
                            create_access_token,
                            create_refresh_token,
                            get_password_hash)
from app.auth.dependencies import get_current_user, get_refresh_token
from app.user.service import TokenService, UsersService
from app.config import settings
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register", status_code=201, summary="Creates a new user")
async def register_user(user_data: UserRegisterSchema):
    """Регистрация пользователя"""
    existing_user = await UsersService.find_one_or_none(email=user_data.email)
    if existing_user:
        raise UserAlreadyExistsException
    hashed_password = get_password_hash(user_data.password)
    await UsersService.add(email=user_data.email,
                       first_name=user_data.first_name,
                       last_name=user_data.last_name,
                       hashed_password=hashed_password,
                       role=UserRole.STUDENT)
    logger.info("Пользователь зарегистрировался")
    return {"message": "Пользователь успешно зарегистрирован"}


@router.post("/login", summary="Logs in a user and returns access and refresh tokens")
async def login_user(response: Response, user_data: UserBaseSchema):
    """Аутенфикация пользователя"""
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise IncorrectEmailOrPasswordException
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    refresh_token = await create_refresh_token({"sub": str(user.id), "role": user.role})
    response.set_cookie("access_token", access_token, httponly=True)
    logger.info(f"Пользователь {user.email} залогинился")
    return {"access_token": access_token,
            "refresh_token": refresh_token}


@router.post("/logout", summary="Deletes tokens")
async def logout_user(response: Response, current_user = Depends(get_current_user)):
    """Выход из системы"""
    response.delete_cookie("access_token")
    await TokenService.delete(user_id=current_user.id) # удаляем refresh токен

@router.post("/test", summary="Creates the test users")
async def create_test_users():
    """Создание тестовых пользователей"""
    users_data = [
        UserTestRegisterSchemas(email="student@example.com",password="password", first_name='Студент', last_name='Тестовый', role=UserRole.STUDENT),
        UserTestRegisterSchemas(email="tutor@example.com", password="password", first_name='Преподаватель', last_name='Тестовый', role=UserRole.TUTOR),
        UserTestRegisterSchemas(email="admin@example.com", password="password", first_name='Администратор', last_name='Тестовый', role=UserRole.ADMIN),
    ]
    
    for user_data in users_data:
        hashed_password = get_password_hash(user_data.password)
        await UsersService.add(email=user_data.email,
                               hashed_password=hashed_password,
                               first_name=user_data.first_name,
                               last_name=user_data.last_name,
                               role=user_data.role)
    logger.info("Были созданы тестовые пользователи")
    return {"message": "Тестовые пользователи успешно созданы"}


@router.post("/token/refresh", summary="Updates the access token")
async def refresh_token(response: Response, refresh: str = Depends(get_refresh_token)):
    """Обновление access токена с помощью refresh токена"""
    try:
        payload = jwt.decode(refresh, settings.SECRET_KEY, settings.ALGORITHM)
        user_id: str = payload.get("sub")
        role = payload.get("role")
        if user_id is None:
            raise IncorrectTokenFormatException
    except InvalidKeyError as e:
        raise IncorrectTokenFormatException from e
    new_access_token = create_access_token({"sub": user_id, "role": role})
    response.set_cookie("access_token", new_access_token, httponly=True)
    logger.info(f"Токен был обновлен для юзера: {user_id} {role}")
    return {"access_token": new_access_token}


@router.get("/me", summary="Returns the info about user", response_model=UserResponseSchema)
async def get_user(current_user: Users = Depends(get_current_user)):
    """Получение информации о пользователе"""
    return current_user
