from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    __tablename__ = 'students'

    id: Optional[int] = Field(default=None, primary_key=True)
    roll_num: str = Field(unique=True, index=True)
    register_num: str = Field(unique=True, index=True)
    name: str
    department: str
    semester: int
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
