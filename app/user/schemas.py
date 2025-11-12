from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator


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
    first_name: str = Field(..., min_length=2, max_length=50, description="Имя")
    last_name: str = Field(..., min_length=2, max_length=50, description="Фамилия")
    role: UserRole
    group: Optional[str] = Field(default=None,
                                 min_length=4,
                                 max_length=7,
                                 description="Номер группы, например, 8В34")
    

    @field_validator('group', mode='before')
    def check_group_first_char(cls, v, info):
        role = info.data.get('role')
        if role == UserRole.STUDENT:
            if not v:
                raise ValueError("Для студента необходимо указать группу.")
            if not v[0].isdigit():
                raise ValueError("Группа должна начинаться с цифры.")
        return v
    
    @field_validator('group')
    @classmethod
    def normalize_group(cls, v, info):
        """Приведение группы к верхнему регистру"""
        role = info.data.get('role')
        if role == 'STUDENT' and v is not None:
            return v.upper().strip()
        return None


class UserTestRegisterSchemas(UserRegisterSchema):
    role: UserRole


class UserResponseSchema(BaseModel):
    id: int
    role: UserRole
    first_name: str
    last_name: str


class CompleteProfileSchema(BaseModel):
    role: str
    group: str | None = None