"""report_service.py — Reporting and export business logic.

Responsibilities:
  - Aggregate per-student marks into subject-level CO attainment summaries.
  - Filter reports by department_id and section_id.
  - Generate CSV exports of mark records and attainment reports.

Rounding policy:
  Store raw floats in the database; round to 2 decimal places only at
  report/display time.
"""

from __future__ import annotations

import csv
import io
from typing import Optional, Sequence

from sqlmodel import Session, select

from app.models.section import Section
from app.models.student import Student
from app.models.student_marks import StudentMarks
from app.models.subject import Subject
from app.schemas.report import SubjectAttainmentReport, SubjectAttainmentRow

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CO_INDICES = (1, 2, 3, 4, 5)
ATTAINMENT_THRESHOLD = 70.0  # 70% threshold


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


def _safe_avg(values: list[float]) -> float:
    """Return the mean of a list, or 0.0 for empty lists."""
    return sum(values) / len(values) if values else 0.0


def _round2(value: float) -> float:
    """Round to 2 decimal places for report display."""
    return round(value, 2)


# ---------------------------------------------------------------------------
# Subject-level attainment report
# ---------------------------------------------------------------------------


def get_subject_attainment_report(
    db: Session,
    subject_id: Optional[int] = None,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
) -> SubjectAttainmentReport:
    """Build a subject-level CO direct attainment summary."""
    stmt = select(Subject)
    if subject_id is not None:
        stmt = stmt.where(Subject.id == subject_id)
    if department_id is not None:
        stmt = stmt.where(Subject.department_id == department_id)

    subjects: Sequence[Subject] = db.exec(stmt).all()
    rows: list[SubjectAttainmentRow] = []

    for subject in subjects:
        marks_stmt = select(StudentMarks).where(StudentMarks.subject_id == subject.id)
        if section_id is not None:
            marks_stmt = marks_stmt.where(StudentMarks.section_id == section_id)
        all_marks: Sequence[StudentMarks] = db.exec(marks_stmt).all()

        if not all_marks:
            rows.append(
                SubjectAttainmentRow(
                    subject_id=subject.id,
                    subject_code=subject.course_code,
                    subject_name=subject.course_name,
                    direct_attainment_co1=0.0,
                    direct_attainment_co2=0.0,
                    direct_attainment_co3=0.0,
                    direct_attainment_co4=0.0,
                    direct_attainment_co5=0.0,
                )
            )
            continue

        avg_da = {
            co: _round2(
                _safe_avg([getattr(m, f'direct_attainment_co{co}') for m in all_marks])
            )
            for co in CO_INDICES
        }

        rows.append(
            SubjectAttainmentRow(
                subject_id=subject.id,
                subject_code=subject.course_code,
                subject_name=subject.course_name,
                direct_attainment_co1=avg_da[1],
                direct_attainment_co2=avg_da[2],
                direct_attainment_co3=avg_da[3],
                direct_attainment_co4=avg_da[4],
                direct_attainment_co5=avg_da[5],
            )
        )

    return SubjectAttainmentReport(rows=rows)


# ---------------------------------------------------------------------------
# CSV export — Marks detail
# ---------------------------------------------------------------------------

_MARKS_CSV_HEADERS = [
    'student_id',
    'roll_num',
    'register_num',
    'student_name',
    'subject_id',
    'course_code',
    'course_name',
    'section_id',
    # Inputs
    'cia_co1', 'cia_co2', 'cia_co3', 'cia_co4', 'cia_co5',
    'assess_co1', 'assess_co2', 'assess_co3', 'assess_co4', 'assess_co5',
    'presentation', 'quiz',
    'endsem_co1', 'endsem_co2', 'endsem_co3', 'endsem_co4', 'endsem_co5',
    # Derived
    'internal_x_co1', 'internal_x_co2', 'internal_x_co3', 'internal_x_co4', 'internal_x_co5',
    'endsem_y_co1', 'endsem_y_co2', 'endsem_y_co3', 'endsem_y_co4', 'endsem_y_co5',
    'direct_attainment_co1', 'direct_attainment_co2', 'direct_attainment_co3',
    'direct_attainment_co4', 'direct_attainment_co5',
]


def export_marks_csv(
    db: Session,
    subject_id: Optional[int] = None,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
) -> str:
    """Export mark records as a CSV string."""
    stmt = select(StudentMarks, Student, Subject).join(
        Student, StudentMarks.student_id == Student.id
    ).join(
        Subject, StudentMarks.subject_id == Subject.id
    )

    if subject_id is not None:
        stmt = stmt.where(StudentMarks.subject_id == subject_id)
    if department_id is not None:
        stmt = stmt.where(Subject.department_id == department_id)
    if section_id is not None:
        stmt = stmt.where(StudentMarks.section_id == section_id)

    results = db.exec(stmt).all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_MARKS_CSV_HEADERS)
    writer.writeheader()

    for marks, student, subject in results:
        row: dict = {
            'student_id': student.id,
            'roll_num': student.roll_num,
            'register_num': student.register_num,
            'student_name': student.name,
            'subject_id': subject.id,
            'course_code': subject.course_code,
            'course_name': subject.course_name,
            'section_id': marks.section_id or '',
        }
        for field in (
            'cia_co1', 'cia_co2', 'cia_co3', 'cia_co4', 'cia_co5',
            'assess_co1', 'assess_co2', 'assess_co3', 'assess_co4', 'assess_co5',
            'presentation', 'quiz',
            'endsem_co1', 'endsem_co2', 'endsem_co3', 'endsem_co4', 'endsem_co5',
        ):
            row[field] = getattr(marks, field)

        for field in (
            'internal_x_co1', 'internal_x_co2', 'internal_x_co3',
            'internal_x_co4', 'internal_x_co5',
            'endsem_y_co1', 'endsem_y_co2', 'endsem_y_co3',
            'endsem_y_co4', 'endsem_y_co5',
            'direct_attainment_co1', 'direct_attainment_co2', 'direct_attainment_co3',
            'direct_attainment_co4', 'direct_attainment_co5',
        ):
            row[field] = _round2(getattr(marks, field))

        writer.writerow(row)

    return output.getvalue()


# ---------------------------------------------------------------------------
# CSV export — Subject attainment summary
# ---------------------------------------------------------------------------

_SUMMARY_CSV_HEADERS = [
    'subject_id', 'course_code', 'course_name',
    'avg_direct_attainment_co1', 'avg_direct_attainment_co2',
    'avg_direct_attainment_co3', 'avg_direct_attainment_co4',
    'avg_direct_attainment_co5',
    'meets_threshold_co1', 'meets_threshold_co2', 'meets_threshold_co3',
    'meets_threshold_co4', 'meets_threshold_co5',
]


def export_attainment_summary_csv(
    db: Session,
    subject_id: Optional[int] = None,
    department_id: Optional[int] = None,
    section_id: Optional[int] = None,
) -> str:
    """Export the subject-level attainment summary as a CSV string."""
    report = get_subject_attainment_report(
        db,
        subject_id=subject_id,
        department_id=department_id,
        section_id=section_id,
    )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_SUMMARY_CSV_HEADERS)
    writer.writeheader()

    for row in report.rows:
        record: dict = {
            'subject_id': row.subject_id,
            'course_code': row.subject_code,
            'course_name': row.subject_name,
        }
        for co in CO_INDICES:
            da_val = getattr(row, f'direct_attainment_co{co}')
            record[f'avg_direct_attainment_co{co}'] = da_val
            record[f'meets_threshold_co{co}'] = 'YES' if da_val >= ATTAINMENT_THRESHOLD else 'NO'

        writer.writerow(record)

    return output.getvalue()
