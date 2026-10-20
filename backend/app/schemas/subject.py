from typing import Optional
from pydantic import BaseModel


class SubjectCreate(BaseModel):
    course_code: str
    course_name: str
    department_id: int
    semester: int
    department: Optional[str] = None


class SubjectRead(BaseModel):
    id: int
    course_code: str
    course_name: str
    department_id: int
    semester: int
    department: Optional[str] = None
