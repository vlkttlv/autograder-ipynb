from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from app.db import Base


class Disciplines(Base):
    __tablename__ = "discipline"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    teachers = relationship(
        "Users",
        secondary="discipline_teacher",
        back_populates="disciplines"
    )

class DisciplineTeacher(Base):
    __tablename__ = "discipline_teacher"
    __table_args__ = (UniqueConstraint("discipline_id", "teacher_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    discipline_id: Mapped[int] = mapped_column(Integer, ForeignKey("discipline.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)
