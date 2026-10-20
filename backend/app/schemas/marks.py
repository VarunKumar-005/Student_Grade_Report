from pydantic import BaseModel


class MarksUpsert(BaseModel):
    student_id: int
    subject_id: int
    cia_co1: float
    cia_co2: float
    cia_co3: float
    cia_co4: float
    cia_co5: float
    assess_co1: float
    assess_co2: float
    assess_co3: float
    assess_co4: float
    assess_co5: float
    presentation: float
    quiz: float
    endsem_co1: float
    endsem_co2: float
    endsem_co3: float
    endsem_co4: float
    endsem_co5: float


class MarksRead(MarksUpsert):
    id: int
    entered_by_faculty_id: int
    internal_x_co1: float
    internal_x_co2: float
    internal_x_co3: float
    internal_x_co4: float
    internal_x_co5: float
    endsem_y_co1: float
    endsem_y_co2: float
    endsem_y_co3: float
    endsem_y_co4: float
    endsem_y_co5: float
    direct_attainment_co1: float
    direct_attainment_co2: float
    direct_attainment_co3: float
    direct_attainment_co4: float
    direct_attainment_co5: float
