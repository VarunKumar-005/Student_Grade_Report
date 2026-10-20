from pydantic import BaseModel


class SubjectAttainmentRow(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    direct_attainment_co1: float
    direct_attainment_co2: float
    direct_attainment_co3: float
    direct_attainment_co4: float
    direct_attainment_co5: float


class SubjectAttainmentReport(BaseModel):
    rows: list[SubjectAttainmentRow]
