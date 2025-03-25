from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Users(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    
    # Связи с таблицами
    refresh_token = relationship("RefreshToken", back_populates="user")
    assignment = relationship("Assignments", back_populates="user")
    # submission = relationship("Submissions", back_populates="user")



class RefreshToken(Base):

    __tablename__ = 'refresh_tokens'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    
    # Связь с таблицей Users
    user = relationship("Users", back_populates="refresh_token")
