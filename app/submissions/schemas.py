from pydantic import BaseModel, EmailStr


class SubmissionsBaseSchema(BaseModel):
    user_id: int
    assignment_id: int
    score: int
    number_of_attempts: int


class SubmissionStats(SubmissionsBaseSchema):
    id: int
    first_name: str
    last_name: str
    email: EmailStr

    class Config:
        from_attributes=True