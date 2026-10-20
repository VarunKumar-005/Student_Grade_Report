"""
department.py — Department ORM model.

A Department is the top-level organisational unit in the college.
Each department is led by one HOD (Head of Department) — a User with role=HOD.

Relationships:
  departments 1──* users (faculty / HOD members)
  departments 1──* subjects
  departments 1──* sections
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Department(SQLModel, table=True):
    __tablename__ = 'departments'

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str = Field(description='Full department name, e.g. Computer Science and Engineering')
    code: str = Field(
        unique=True,
        index=True,
        description='Short department code, e.g. CSE',
    )

    # The user designated as Head of Department for this department (role=HOD)
    hod_id: Optional[int] = Field(
        default=None,
        foreign_key='users.id',
        nullable=True,
        description='FK → users.id of the HOD user',
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
