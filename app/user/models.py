from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Users(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("group.id"), nullable=True
    )

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Google OAuth
    google_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    google_token: Mapped[str | None] = mapped_column(
        String(1024), nullable=True
    )

    # Relations
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    assignments = relationship("Assignments", back_populates="user")
    submissions = relationship("Submissions", back_populates="user")
    group = relationship("Groups", back_populates="students")
    disciplines = relationship("Disciplines", secondary="discipline_teacher", back_populates="teachers")

    def __repr__(self):
        return f"<User {self.email}>"
