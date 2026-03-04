from datetime import date, datetime, time
from uuid import uuid4
from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base


class Assignments(Base):
    __tablename__ = "assignment"
    __table_args__ = (
        Index("ix_assignment_user_id", "user_id"),
        Index("ix_assignment_discipline_id", "discipline_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_time: Mapped[time] = mapped_column(Time, nullable=False)
    number_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    discipline_id: Mapped[int] = mapped_column(
        ForeignKey("discipline.id"), nullable=False
    )

    # Связи с другими таблицами
    user = relationship("Users", back_populates="assignments")
    discipline = relationship("Disciplines")
    submissions = relationship("Submissions", back_populates="assignment")
    assignment_files = relationship(
        "AssignmentFile",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class AssignmentFile(Base):
    __tablename__ = "assignment_file"
    __table_args__ = (
        Index("ix_assignment_file_assignment_id", "assignment_id"),
        Index(
            "ix_assignment_file_assignment_id_file_type",
            "assignment_id",
            "file_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignment.id"))
    file_type: Mapped[str] = mapped_column(String)  # original / modified
    file_id: Mapped[str] = mapped_column(String)  # путь в Dropbox
    file_link: Mapped[str] = mapped_column(
        String, nullable=False
    )  # публичная ссылка

    assignment = relationship("Assignments", back_populates="assignment_files")
