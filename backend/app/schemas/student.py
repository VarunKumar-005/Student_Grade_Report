from pydantic import BaseModel


class StudentCreate(BaseModel):
    roll_num: str
    register_num: str
    name: str
    department: str
    semester: int


class StudentRead(StudentCreate):
    id: int
