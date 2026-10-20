from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class FacultySubjectAssignment(SQLModel, table=True):
    __tablename__ = 'faculty_subject_assignments'

    id: Optional[int] = Field(default=None, primary_key=True)
    faculty_id: int = Field(foreign_key='users.id', nullable=False, index=True)
    subject_id: int = Field(foreign_key='subjects.id', nullable=False, index=True)
    academic_year: str
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
