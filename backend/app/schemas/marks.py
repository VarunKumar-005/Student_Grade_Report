from typing import Optional
from pydantic import BaseModel, Field, model_validator


class MarksUpsert(BaseModel):
    """Payload for inserting or updating one student's marks in one subject.

    Validation ranges follow the Excel sheet spec:
      CIA per CO  : 0–40
      Assignment  : 0–10
      Presentation: 0–100
      Quiz        : 0–100
      EndSem per CO: 0–20
    """

    student_id: int
    subject_id: int
    section_id: Optional[int] = Field(default=None, description='Optional section / class ID')

    # CIA marks (0–40 each)
    cia_co1: float = Field(ge=0, le=40, description='CIA marks for CO1 (max 40)')
    cia_co2: float = Field(ge=0, le=40, description='CIA marks for CO2 (max 40)')
    cia_co3: float = Field(ge=0, le=40, description='CIA marks for CO3 (max 40)')
    cia_co4: float = Field(ge=0, le=40, description='CIA marks for CO4 (max 40)')
    cia_co5: float = Field(ge=0, le=40, description='CIA marks for CO5 (max 40)')

    # Assignment marks (0–10 each)
    assess_co1: float = Field(ge=0, le=10, description='Assignment marks for CO1 (max 10)')
    assess_co2: float = Field(ge=0, le=10, description='Assignment marks for CO2 (max 10)')
    assess_co3: float = Field(ge=0, le=10, description='Assignment marks for CO3 (max 10)')
    assess_co4: float = Field(ge=0, le=10, description='Assignment marks for CO4 (max 10)')
    assess_co5: float = Field(ge=0, le=10, description='Assignment marks for CO5 (max 10)')

    # Shared internal marks
    presentation: float = Field(ge=0, le=100, description='Presentation / Tutorial mark (max 100)')
    quiz: float = Field(ge=0, le=100, description='Quiz mark (max 100)')

    # End-semester marks (0–20 each)
    endsem_co1: float = Field(ge=0, le=20, description='End-semester marks for CO1 (max 20)')
    endsem_co2: float = Field(ge=0, le=20, description='End-semester marks for CO2 (max 20)')
    endsem_co3: float = Field(ge=0, le=20, description='End-semester marks for CO3 (max 20)')
    endsem_co4: float = Field(ge=0, le=20, description='End-semester marks for CO4 (max 20)')
    endsem_co5: float = Field(ge=0, le=20, description='End-semester marks for CO5 (max 20)')


class BulkMarksUpsert(BaseModel):
    """Payload for bulk mark entry — multiple students for one subject at once."""

    subject_id: int = Field(description='Subject to which all records belong')
    section_id: Optional[int] = Field(default=None, description='Optional section / class ID')
    records: list[MarksUpsert] = Field(
        min_length=1,
        max_length=500,
        description='List of per-student mark payloads (student_id must match subject_id above)',
    )

    @model_validator(mode='after')
    def validate_all_same_subject(self) -> 'BulkMarksUpsert':
        for i, r in enumerate(self.records):
            if r.subject_id != self.subject_id:
                raise ValueError(
                    f'records[{i}].subject_id={r.subject_id} does not match '
                    f'envelope subject_id={self.subject_id}'
                )
        return self


class BulkUpsertResult(BaseModel):
    """Result summary for a bulk upsert operation."""

    inserted: int = Field(description='Number of new records created')
    updated: int = Field(description='Number of existing records updated')
    records: list['MarksRead'] = Field(description='All upserted records with derived fields')


class MarksRead(MarksUpsert):
    """Full mark record including auto-calculated CO attainment fields."""

    id: int
    entered_by_faculty_id: int

    # Derived — Internal X per CO (0–100 %)
    internal_x_co1: float
    internal_x_co2: float
    internal_x_co3: float
    internal_x_co4: float
    internal_x_co5: float

    # Derived — EndSem Y per CO (0–100 %)
    endsem_y_co1: float
    endsem_y_co2: float
    endsem_y_co3: float
    endsem_y_co4: float
    endsem_y_co5: float

    # Derived — Direct Attainment per CO (0–100 %)
    direct_attainment_co1: float
    direct_attainment_co2: float
    direct_attainment_co3: float
    direct_attainment_co4: float
    direct_attainment_co5: float


class PaginatedMarksResponse(BaseModel):
    """Paginated wrapper for mark records."""

    total: int = Field(description='Total records matching the filter')
    page: int = Field(description='Current page number (1-indexed)')
    page_size: int = Field(description='Records per page')
    pages: int = Field(description='Total number of pages')
    data: list[MarksRead]


class MarksPreview(BaseModel):
    """Preview of calculated CO attainment without persisting to the database.

    Useful for showing real-time calculation results as faculty type.
    """

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


# Resolve forward ref
BulkUpsertResult.model_rebuild()

