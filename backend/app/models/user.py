from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    SUPER_ADMIN = 'SUPER_ADMIN'   # Institution-level — manages Departments and HODs
    HOD = 'HOD'                   # Department head — manages Faculty, Subjects, Sections
    FACULTY = 'FACULTY'           # Teaching staff — enters marks for assigned sections
    ADMIN = 'ADMIN'               # Legacy alias — treated as SUPER_ADMIN in permission checks


class User(SQLModel, table=True):
    __tablename__ = 'users'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    password_hash: str
    role: UserRole = Field(default=UserRole.FACULTY)

    # HOD and FACULTY are scoped to one department; SUPER_ADMIN/ADMIN have no restriction
    department_id: Optional[int] = Field(
        default=None,
        foreign_key='departments.id',
        nullable=True,
        index=True,
    )

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

