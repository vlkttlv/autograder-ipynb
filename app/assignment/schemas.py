from datetime import date, time
from pydantic import BaseModel, Field

class AssignmentBaseSchema(BaseModel):
    name: str
    start_date: date
    start_time: time
    due_date: date
    due_time: time
    number_of_attempts: int = Field(..., ge=1)


class AssignmentResponseSchema(AssignmentBaseSchema):
    user_id: int
    grade: int


class AssignmentUpdateSchema(AssignmentBaseSchema):
    pass