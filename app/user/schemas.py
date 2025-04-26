from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    TUTOR = "TUTOR"
    ADMIN = "ADMIN"


class UserBaseSchema(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=8, max_length=50, description="Пароль, от 8 до 50 знаков")
    
class UserLoginSchema(UserBaseSchema):
    pass


class UserRegisterSchema(UserBaseSchema):
    first_name: str
    last_name: str


class UserTestRegisterSchemas(UserRegisterSchema):
    role: UserRole

    
class UserResponseSchema(UserRegisterSchema):
    id: int
    role: UserRole
