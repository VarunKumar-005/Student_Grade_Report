"""
section.py — Section (Class) and SectionStudents ORM models.

A Section represents one physical class group within a department for a given
semester and academic year. For example:
  - "III-CSE-A"  →  3rd year CSE, Section A, 2025-26
  - "II-ECE-B"   →  2nd year ECE, Section B, 2025-26

SectionStudents is the enrollment bridge table linking Students to Sections.
A student may be enrolled in exactly one section per semester/year.

Relationships:
  departments 1──* sections
  sections    *──* students   (via section_students)
  sections    1──* faculty_subject_assignments
  sections    1──* student_marks
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Section(SQLModel, table=True):
    __tablename__ = 'sections'

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(
        description='Section label, e.g. "A", "B", or "III-CSE-A"'
    )
    department_id: int = Field(
        foreign_key='departments.id',
        nullable=False,
        index=True,
        description='FK → departments.id',
    )
    semester: int = Field(description='Semester number (1–8)')
    academic_year: str = Field(
        description='Academic year string, e.g. "2025-26"'
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class SectionStudents(SQLModel, table=True):
    """Enrollment bridge — maps one student to one section."""

    __tablename__ = 'section_students'
    __table_args__ = (
        UniqueConstraint('section_id', 'student_id', name='uq_section_student'),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    section_id: int = Field(
        foreign_key='sections.id',
        nullable=False,
        index=True,
    )
    student_id: int = Field(
        foreign_key='students.id',
        nullable=False,
        index=True,
    )

    enrolled_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
