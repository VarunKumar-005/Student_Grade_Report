from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
    name: str = Field(description='Section name e.g. "A" or "III-CSE-A"')
    department_id: int
    semester: int
    academic_year: str


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[int] = None
    semester: Optional[int] = None
    academic_year: Optional[str] = None


class SectionRead(BaseModel):
    id: int
    name: str
    department_id: int
    semester: int
    academic_year: str
    created_at: datetime
    updated_at: datetime


class SectionStudentEnroll(BaseModel):
    student_id: int


class SectionStudentCreateAndEnroll(BaseModel):
    roll_num: str
    register_num: str
    name: str
    semester: Optional[int] = None


class SectionStudentBulkEnroll(BaseModel):
    students: list[SectionStudentCreateAndEnroll]


class SectionStudentRead(BaseModel):
    id: int
    section_id: int
    student_id: int
    student_name: Optional[str] = None
    student_roll: Optional[str] = None
    student_reg: Optional[str] = None
    enrolled_at: datetime
