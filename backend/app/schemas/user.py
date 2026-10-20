from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.FACULTY


class UserRead(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: UserRole
