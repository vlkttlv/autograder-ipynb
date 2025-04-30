from datetime import date, time
from uuid import uuid4
from sqlalchemy import Date, ForeignKey, Integer, String, Time, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db import Base

class Assignments(Base):

    __tablename__ = "assignments"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True)
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    due_date: Mapped[date] = mapped_column(Date)
    due_time: Mapped[time] = mapped_column(Time)
    number_of_attempts: Mapped[int]
    grade: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))

    # Связи с другими таблицами
    user = relationship("Users", back_populates="assignment")
    submission = relationship("Submissions", back_populates="assignment")
    assignment_files = relationship("AssignmentFile", back_populates="assignment")



class AssignmentFile(Base):
    __tablename__ = "assignment_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assignment_id = mapped_column(ForeignKey("assignments.id"))
    file_type = mapped_column(String)  # original / modified
    content = mapped_column(LargeBinary)

    assignment = relationship("Assignments", back_populates="assignment_files")