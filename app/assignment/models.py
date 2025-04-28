from datetime import date, time
from sqlalchemy import Date, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

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
