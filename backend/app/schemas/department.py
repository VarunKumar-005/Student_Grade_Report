from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str
    code: str
    hod_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    hod_id: Optional[int] = None


class DepartmentHODAssign(BaseModel):
    user_id: int


class DepartmentRead(BaseModel):
    id: int
    name: str
    code: str
    hod_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
