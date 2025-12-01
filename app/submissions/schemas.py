from uuid import UUID
from fastapi import Query
from pydantic import BaseModel, EmailStr

from app.assignment.schemas import SortEnum


class SubmissionsBaseSchema(BaseModel):
    user_id: int
    assignment_id: int
    score: int
    number_of_attempts: int


class SubmissionStats(SubmissionsBaseSchema):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr

    class Config:
        from_attributes = True


class SubmissionQueryParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Номер страницы"),
        limit: int = Query(
            10, gt=0, le=100, description="Количество записей на странице"
        ),
        sort: SortEnum = Query(
            SortEnum.newest,
            description="Сортировка: newest - сначала новые / oldest - сначала старые",
        ),
    ):
        self.page = page
        self.limit = limit
        self.sort = sort
