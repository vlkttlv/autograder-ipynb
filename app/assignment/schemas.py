from datetime import date, time
from enum import Enum
from pydantic import BaseModel, Field

class AssignmentBaseSchema(BaseModel):
    name: str = None
    start_date: date = None
    start_time: time = None
    due_date: date = None
    due_time: time = None
    number_of_attempts: int = Field(None, ge=1)


class AssignmentResponseSchema(AssignmentBaseSchema):
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