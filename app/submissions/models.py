from sqlalchemy import JSON, ForeignKey, Integer, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4
from app.db import Base


class Submissions(Base):

    __tablename__ = "submission"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    assignment_id: Mapped[UUID] = mapped_column(ForeignKey('assignments.id'))
    score: Mapped[int] = mapped_column(Integer)
    number_of_attempts: Mapped[int]
    feedback: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Связи с другими таблицами
    user = relationship("Users", back_populates="submission")
    assignment = relationship("Assignments", back_populates="submission")
    submission_files = relationship("SubmissionFiles", back_populates="submission")


class SubmissionFiles(Base):
    __tablename__ = "submission_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id = mapped_column(ForeignKey("submission.id"))
    assignment_id = mapped_column(ForeignKey("assignments.id"))
    content = mapped_column(LargeBinary)

    submission = relationship("Submissions", back_populates="submission_files")
