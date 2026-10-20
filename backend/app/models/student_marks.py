from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class StudentMarks(SQLModel, table=True):
    __tablename__ = 'student_marks'

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key='students.id', nullable=False, index=True)
    subject_id: int = Field(foreign_key='subjects.id', nullable=False, index=True)
    entered_by_faculty_id: int = Field(foreign_key='users.id', nullable=False)

    cia_co1: float = 0
    cia_co2: float = 0
    cia_co3: float = 0
    cia_co4: float = 0
    cia_co5: float = 0

    assess_co1: float = 0
    assess_co2: float = 0
    assess_co3: float = 0
    assess_co4: float = 0
    assess_co5: float = 0

    presentation: float = 0
    quiz: float = 0

    endsem_co1: float = 0
    endsem_co2: float = 0
    endsem_co3: float = 0
    endsem_co4: float = 0
    endsem_co5: float = 0

    internal_x_co1: float = 0
    internal_x_co2: float = 0
    internal_x_co3: float = 0
    internal_x_co4: float = 0
    internal_x_co5: float = 0

    endsem_y_co1: float = 0
    endsem_y_co2: float = 0
    endsem_y_co3: float = 0
    endsem_y_co4: float = 0
    endsem_y_co5: float = 0

    direct_attainment_co1: float = 0
    direct_attainment_co2: float = 0
    direct_attainment_co3: float = 0
    direct_attainment_co4: float = 0
    direct_attainment_co5: float = 0

    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
