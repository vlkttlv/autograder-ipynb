from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.db import Base


class Submissions(Base):
    __tablename__ = "submission"
    __table_args__ = (
        Index("ix_submission_user_id", "user_id"),
        Index("ix_submission_assignment_id", "assignment_id"),
        Index("ix_submission_user_id_assignment_id", "user_id", "assignment_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignment.id"))
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    number_of_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    

    # Связи с другими таблицами
    user = relationship("Users", back_populates="submissions")
    assignment = relationship("Assignments", back_populates="submissions")
    submission_files = relationship(
        "SubmissionFiles", back_populates="submission", cascade="all, delete-orphan"
    )
    attempts = relationship(
        "SubmissionAttempt", back_populates="submission", cascade="all, delete-orphan"
    )


class SubmissionFiles(Base):
    __tablename__ = "submission_file"
    __table_args__ = (
        Index("ix_submission_file_submission_id", "submission_id"),
        Index("ix_submission_file_assignment_id", "assignment_id"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey("submission.id", ondelete="CASCADE")
    )
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignment.id"))
    file_id: Mapped[str] = mapped_column(String)  # путь в Dropbox
    file_link: Mapped[str] = mapped_column(
        String, nullable=False
    )  # публичная ссылка

    submission = relationship("Submissions", back_populates="submission_files")


class SubmissionAttempt(Base):
    __tablename__ = "submission_attempt"
    __table_args__ = (
        Index("ix_submission_attempt_submission_id", "submission_id"),
        Index("ix_submission_attempt_user_id", "user_id"),
        Index("ix_submission_attempt_assignment_id", "assignment_id"),
    )

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True
    )
    submission_id: Mapped[UUID] = mapped_column(
        ForeignKey("submission.id", ondelete="CASCADE")
    )
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignment.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    file_link: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission = relationship("Submissions", back_populates="attempts")