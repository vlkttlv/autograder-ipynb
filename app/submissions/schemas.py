from pydantic import BaseModel


class SubmissionsBaseSchema(BaseModel):
    user_id: str
    assignment_id: int
    score: int
    number_of_attempts: int