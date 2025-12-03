from datetime import date, time
from enum import Enum
from typing import List, Optional
from uuid import UUID
from fastapi import Query
from pydantic import BaseModel, Field


class AssignmentBaseSchema(BaseModel):
    name: str = None
    start_date: date = None
    start_time: time = None
    due_date: date = None
    due_time: time = None
    number_of_attempts: int = Field(None, ge=1)


class AssignmentResponseSchema(AssignmentBaseSchema):
    id: UUID
    user_id: int
    grade: int
    discipline_id: int


class AssignmentUpdateSchema(BaseModel):
    name: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    number_of_attempts: Optional[int] = Field(None, ge=1)
    discipline_id: Optional[int] = None
    new_discipline_name: Optional[str] = None


class TypeOfAssignmentFile(str, Enum):
    ORIGINAL = "ORIGINAL"
    MODIFIED = "MODIFIED"


class ExportMethod(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class AssignmentListResponse(BaseModel):
    assignments: List[AssignmentResponseSchema]
    total: int


class SortEnum(str, Enum):
    newest = "newest"
    oldest = "oldest"


class UserStatsResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    group_id: int


class SubmissionStatsResponse(BaseModel):
    id: UUID
    user_id: int
    assignment_id: UUID
    score: int
    number_of_attempts: int
    feedback: list
    user: UserStatsResponse


class StatsResponse(BaseModel):
    submissions: list[SubmissionStatsResponse]
    average_score: float
    total: int


class AssignmentQueryParams:
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
