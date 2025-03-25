from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    STUDENT = "STUDENT"
    TUTOR = "TUTOR"
    ADMIN = "ADMIN"


class UserBaseSchema(BaseModel):
    email: EmailStr = Field(..., description="Электронная почта")
    password: str = Field(..., min_length=8, max_length=50, description="Пароль, от 8 до 50 знаков")
    

class UserRegisterSchema(UserBaseSchema):
    role: UserRole


class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    role: UserRole