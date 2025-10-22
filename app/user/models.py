from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Users(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"), nullable=True)
    
    # Связи с таблицами
    refresh_token = relationship("RefreshToken", back_populates="user")
    assignment = relationship("Assignments", back_populates="user")
    submission = relationship("Submissions", back_populates="user")
    group = relationship("Groups", back_populates="students")
    disciplines = relationship("Disciplines", back_populates="teacher")

    def __str__(self):
        return f"Пользователь {self.email}"


class RefreshToken(Base):

    __tablename__ = 'refresh_tokens'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    
    # Связь с таблицей Users
    user = relationship("Users", back_populates="refresh_token")


class Groups(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # связь со студентами
    students = relationship("Users", back_populates="group")

    def __str__(self):
        return f"Группа {self.name}"


class Disciplines(Base):
    __tablename__ = "disciplines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    teacher = relationship("Users", back_populates="disciplines")

    def __str__(self):
        return f"Дисциплина {self.name}"
