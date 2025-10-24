from datetime import date, time
from enum import Enum
from typing import List
from uuid import UUID
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


class AssignmentUpdateSchema(AssignmentBaseSchema):
    pass


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
