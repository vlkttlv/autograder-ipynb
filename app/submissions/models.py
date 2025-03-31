from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Submissions(Base):

    __tablename__ = "submission"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    assignment_id: Mapped[int] = mapped_column(ForeignKey('assignments.id'))
    score: Mapped[int] = mapped_column(Integer)
    number_of_attempts: Mapped[int]

    # Связи с другими таблицами
    user = relationship("Users", back_populates="submission")
    assignment = relationship("Assignments", back_populates="submission")
