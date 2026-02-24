from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, UniqueConstraint
from app.db import Base


class Disciplines(Base):
    __tablename__ = "disciplines"
    __table_args__ = (
        UniqueConstraint("teacher_id", "name", name="uq_teacher_discipline"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    teacher = relationship("Users", back_populates="disciplines")
    assignments = relationship("Assignments", back_populates="discipline")
