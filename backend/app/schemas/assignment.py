from pydantic import BaseModel


class AssignmentCreate(BaseModel):
    faculty_id: int
    subject_id: int
    section_id: int
    academic_year: str


class AssignmentRead(AssignmentCreate):
    id: int
