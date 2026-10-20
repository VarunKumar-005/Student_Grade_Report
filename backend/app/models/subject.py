"""
subject.py — Subject / Course ORM model.

A Subject belongs to a Department and is offered in a specific semester.
Faculty are linked to Subjects via FacultySubjectAssignments (which also
carry a Section reference so two faculty can teach the same subject to
different sections independently).
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Subject(SQLModel, table=True):
    __tablename__ = 'subjects'

    id: Optional[int] = Field(default=None, primary_key=True)
    course_code: str = Field(unique=True, index=True)
    course_name: str

    # Owned by a Department (FK replaces the old plain string field)
    department_id: int = Field(
        foreign_key='departments.id',
        nullable=False,
        index=True,
        description='FK → departments.id',
    )
    semester: int

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

