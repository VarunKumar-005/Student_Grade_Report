from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Subject(SQLModel, table=True):
    __tablename__ = 'subjects'

    id: Optional[int] = Field(default=None, primary_key=True)
    course_code: str = Field(unique=True, index=True)
    course_name: str
    department: str
    semester: int
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
