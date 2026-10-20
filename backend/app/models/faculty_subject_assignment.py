"""
faculty_subject_assignment.py — Faculty → Subject → Section assignment.

Links one faculty member to one subject for one section in one academic year.
This replaces the simpler Faculty → Subject model and allows two faculty to
independently teach the same subject to different sections.

Unique constraint: (faculty_id, subject_id, section_id, academic_year) prevents
double-assigning the same faculty to the same subject+section in the same year.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class FacultySubjectAssignment(SQLModel, table=True):
    __tablename__ = 'faculty_subject_assignments'
    __table_args__ = (
        UniqueConstraint(
            'faculty_id', 'subject_id', 'section_id', 'academic_year',
            name='uq_faculty_subject_section_year',
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    faculty_id: int = Field(
        foreign_key='users.id',
        nullable=False,
        index=True,
    )
    subject_id: int = Field(
        foreign_key='subjects.id',
        nullable=False,
        index=True,
    )
    section_id: int = Field(
        foreign_key='sections.id',
        nullable=False,
        index=True,
        description='The class/section this assignment covers',
    )
    academic_year: str = Field(description='e.g. "2025-26"')

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

