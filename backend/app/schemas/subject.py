from pydantic import BaseModel


class SubjectCreate(BaseModel):
    course_code: str
    course_name: str
    department: str
    semester: int


class SubjectRead(SubjectCreate):
    id: int
