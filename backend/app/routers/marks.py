"""marks.py — Mark entry and retrieval router.

Endpoints:
    POST   /marks/upsert          — insert or update marks for one student-subject pair
    POST   /marks/bulk-upsert     — bulk insert/update marks for many students at once
    POST   /marks/preview         — calculate CO attainment without saving (dry-run)
    GET    /marks/                — paginated list of mark records (with filters)
    GET    /marks/my-subjects     — marks summary for subjects assigned to current faculty
    GET    /marks/{id}            — retrieve a single mark record
    DELETE /marks/{id}            — delete a mark record (SuperAdmin only)

On every upsert the Attainment Calculation Engine recalculates and persists
Internal X, EndSem Y, and Direct Attainment for each CO automatically.
"""

import math
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import func, select

from app.deps import AdminUser, CurrentUser, DBSession
from app.models.department import Department
from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.section import Section
from app.models.student import Student
from app.models.student_marks import StudentMarks
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.marks import (
    BulkMarksUpsert,
    BulkUpsertResult,
    MarksPreview,
    MarksRead,
    MarksUpsert,
    PaginatedMarksResponse,
)
from app.services.calculation_service import apply_attainment_to_marks_row, calculate_attainment

router = APIRouter(prefix='/marks', tags=['Marks'])


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _verify_user_subject_access(
    db: DBSession,
    user: User,
    subject_id: int,
    section_id: Optional[int] = None,
) -> None:
    """Ensure user has authorization to enter/view marks for this subject + section.
    
    - SUPER_ADMIN / ADMIN bypass.
    - HOD has access if subject belongs to their department.
    - FACULTY has access if an assignment links them to this subject (and section).
    """
    if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        return

    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')

    if user.role == UserRole.HOD:
        if subject.department_id != user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Subject does not belong to your department.',
            )
        return

    # For FACULTY:
    stmt = select(FacultySubjectAssignment).where(
        FacultySubjectAssignment.faculty_id == user.id,
        FacultySubjectAssignment.subject_id == subject_id,
    )
    if section_id is not None:
        stmt = stmt.where(FacultySubjectAssignment.section_id == section_id)

    assignment = db.exec(stmt).first()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='You are not assigned to this subject / section.',
        )


def _marks_to_read(m: StudentMarks) -> MarksRead:
    """Map a StudentMarks ORM instance to its Pydantic response schema."""
    return MarksRead(
        id=m.id,
        student_id=m.student_id,
        subject_id=m.subject_id,
        section_id=m.section_id,
        entered_by_faculty_id=m.entered_by_faculty_id,
        cia_co1=m.cia_co1, cia_co2=m.cia_co2, cia_co3=m.cia_co3,
        cia_co4=m.cia_co4, cia_co5=m.cia_co5,
        assess_co1=m.assess_co1, assess_co2=m.assess_co2, assess_co3=m.assess_co3,
        assess_co4=m.assess_co4, assess_co5=m.assess_co5,
        presentation=m.presentation, quiz=m.quiz,
        endsem_co1=m.endsem_co1, endsem_co2=m.endsem_co2, endsem_co3=m.endsem_co3,
        endsem_co4=m.endsem_co4, endsem_co5=m.endsem_co5,
        internal_x_co1=m.internal_x_co1, internal_x_co2=m.internal_x_co2,
        internal_x_co3=m.internal_x_co3, internal_x_co4=m.internal_x_co4,
        internal_x_co5=m.internal_x_co5,
        endsem_y_co1=m.endsem_y_co1, endsem_y_co2=m.endsem_y_co2,
        endsem_y_co3=m.endsem_y_co3, endsem_y_co4=m.endsem_y_co4,
        endsem_y_co5=m.endsem_y_co5,
        direct_attainment_co1=m.direct_attainment_co1,
        direct_attainment_co2=m.direct_attainment_co2,
        direct_attainment_co3=m.direct_attainment_co3,
        direct_attainment_co4=m.direct_attainment_co4,
        direct_attainment_co5=m.direct_attainment_co5,
    )


def _run_calculation(payload: MarksUpsert):
    """Run the CO attainment calculation engine against a MarksUpsert payload."""
    return calculate_attainment(
        cia_co1=payload.cia_co1, cia_co2=payload.cia_co2,
        cia_co3=payload.cia_co3, cia_co4=payload.cia_co4, cia_co5=payload.cia_co5,
        assess_co1=payload.assess_co1, assess_co2=payload.assess_co2,
        assess_co3=payload.assess_co3, assess_co4=payload.assess_co4, assess_co5=payload.assess_co5,
        presentation=payload.presentation, quiz=payload.quiz,
        endsem_co1=payload.endsem_co1, endsem_co2=payload.endsem_co2,
        endsem_co3=payload.endsem_co3, endsem_co4=payload.endsem_co4, endsem_co5=payload.endsem_co5,
    )


def _upsert_one(
    db: DBSession,
    payload: MarksUpsert,
    faculty_id: int,
) -> tuple[MarksRead, bool]:
    """Insert or update a single StudentMarks record."""
    result = _run_calculation(payload)
    existing = db.exec(
        select(StudentMarks).where(
            StudentMarks.student_id == payload.student_id,
            StudentMarks.subject_id == payload.subject_id,
        )
    ).first()

    if existing is not None:
        for co in range(1, 6):
            setattr(existing, f'cia_co{co}', getattr(payload, f'cia_co{co}'))
            setattr(existing, f'assess_co{co}', getattr(payload, f'assess_co{co}'))
            setattr(existing, f'endsem_co{co}', getattr(payload, f'endsem_co{co}'))
        existing.presentation = payload.presentation
        existing.quiz = payload.quiz
        existing.entered_by_faculty_id = faculty_id
        if payload.section_id is not None:
            existing.section_id = payload.section_id
        existing.updated_at = datetime.utcnow()
        apply_attainment_to_marks_row(existing, result)
        db.add(existing)
        db.flush()
        return _marks_to_read(existing), False
    else:
        marks = StudentMarks(
            student_id=payload.student_id,
            subject_id=payload.subject_id,
            section_id=payload.section_id,
            entered_by_faculty_id=faculty_id,
            cia_co1=payload.cia_co1, cia_co2=payload.cia_co2,
            cia_co3=payload.cia_co3, cia_co4=payload.cia_co4, cia_co5=payload.cia_co5,
            assess_co1=payload.assess_co1, assess_co2=payload.assess_co2,
            assess_co3=payload.assess_co3, assess_co4=payload.assess_co4, assess_co5=payload.assess_co5,
            presentation=payload.presentation, quiz=payload.quiz,
            endsem_co1=payload.endsem_co1, endsem_co2=payload.endsem_co2,
            endsem_co3=payload.endsem_co3, endsem_co4=payload.endsem_co4, endsem_co5=payload.endsem_co5,
        )
        apply_attainment_to_marks_row(marks, result)
        db.add(marks)
        db.flush()
        return _marks_to_read(marks), True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    '/upsert',
    response_model=MarksRead,
    summary='Insert or update marks for one student-subject pair',
)
def upsert_marks(
    payload: MarksUpsert,
    db: DBSession,
    current_user: CurrentUser,
) -> MarksRead:
    if db.get(Student, payload.student_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Student not found')
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')

    _verify_user_subject_access(db, current_user, payload.subject_id, payload.section_id)

    marks_read, _ = _upsert_one(db, payload, current_user.id)
    db.commit()
    return marks_read


@router.post(
    '/bulk-upsert',
    response_model=BulkUpsertResult,
    summary='Bulk insert or update marks for multiple students in one subject',
)
def bulk_upsert_marks(
    payload: BulkMarksUpsert,
    db: DBSession,
    current_user: CurrentUser,
) -> BulkUpsertResult:
    if db.get(Subject, payload.subject_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')

    _verify_user_subject_access(db, current_user, payload.subject_id, payload.section_id)

    inserted_count = 0
    updated_count = 0
    results: list[MarksRead] = []
    missing_students: list[int] = []

    for record in payload.records:
        if db.get(Student, record.student_id) is None:
            missing_students.append(record.student_id)
            continue
        # Inherit section_id from envelope if not specified on item
        if record.section_id is None and payload.section_id is not None:
            record.section_id = payload.section_id
        marks_read, was_inserted = _upsert_one(db, record, current_user.id)
        results.append(marks_read)
        if was_inserted:
            inserted_count += 1
        else:
            updated_count += 1

    if missing_students:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                'message': 'Some student IDs not found in the database',
                'missing_student_ids': missing_students,
            },
        )

    db.commit()
    return BulkUpsertResult(
        inserted=inserted_count,
        updated=updated_count,
        records=results,
    )


@router.post(
    '/preview',
    response_model=MarksPreview,
    summary='Preview CO attainment calculation without saving',
)
def preview_marks(
    payload: MarksUpsert,
    _user: CurrentUser,
) -> MarksPreview:
    result = _run_calculation(payload)
    return MarksPreview(
        internal_x_co1=result.internal_x_co1,
        internal_x_co2=result.internal_x_co2,
        internal_x_co3=result.internal_x_co3,
        internal_x_co4=result.internal_x_co4,
        internal_x_co5=result.internal_x_co5,
        endsem_y_co1=result.endsem_y_co1,
        endsem_y_co2=result.endsem_y_co2,
        endsem_y_co3=result.endsem_y_co3,
        endsem_y_co4=result.endsem_y_co4,
        endsem_y_co5=result.endsem_y_co5,
        direct_attainment_co1=result.direct_attainment_co1,
        direct_attainment_co2=result.direct_attainment_co2,
        direct_attainment_co3=result.direct_attainment_co3,
        direct_attainment_co4=result.direct_attainment_co4,
        direct_attainment_co5=result.direct_attainment_co5,
    )


@router.get(
    '/my-subjects',
    response_model=list[dict],
    summary='Get mark entry status for all subjects assigned to me (Faculty)',
)
def get_my_subjects_marks_status(
    db: DBSession,
    current_user: CurrentUser,
) -> list[dict]:
    """Return per-subject mark entry progress for the currently logged-in faculty."""
    assignments = db.exec(
        select(FacultySubjectAssignment).where(
            FacultySubjectAssignment.faculty_id == current_user.id
        )
    ).all()

    summary = []
    for assignment in assignments:
        subject = db.get(Subject, assignment.subject_id)
        if subject is None:
            continue

        section = db.get(Section, assignment.section_id)
        dept = db.get(Department, subject.department_id)

        # Count students with marks entered for this subject and section
        stmt = select(func.count(StudentMarks.id)).where(
            StudentMarks.subject_id == assignment.subject_id
        )
        if assignment.section_id is not None:
            stmt = stmt.where(StudentMarks.section_id == assignment.section_id)
        entered_count = db.exec(stmt).one()

        summary.append({
            'subject_id': subject.id,
            'course_code': subject.course_code,
            'course_name': subject.course_name,
            'department': dept.code if dept else None,
            'department_id': subject.department_id,
            'section_id': assignment.section_id,
            'section_name': section.name if section else None,
            'semester': subject.semester,
            'academic_year': assignment.academic_year,
            'marks_entered': entered_count,
        })

    return summary


@router.get(
    '/',
    response_model=PaginatedMarksResponse,
    summary='List mark records (paginated)',
)
def list_marks(
    db: DBSession,
    current_user: CurrentUser,
    subject_id: Optional[int] = Query(default=None, description='Filter by subject ID'),
    student_id: Optional[int] = Query(default=None, description='Filter by student ID'),
    section_id: Optional[int] = Query(default=None, description='Filter by section ID'),
    page: int = Query(default=1, ge=1, description='Page number (1-indexed)'),
    page_size: int = Query(default=50, ge=1, le=200, description='Records per page (max 200)'),
) -> PaginatedMarksResponse:
    base_stmt = select(StudentMarks)

    if current_user.role == UserRole.FACULTY:
        assigned_stmt = select(FacultySubjectAssignment.subject_id).where(
            FacultySubjectAssignment.faculty_id == current_user.id
        )
        assigned_ids = list(db.exec(assigned_stmt).all())
        base_stmt = base_stmt.where(StudentMarks.subject_id.in_(assigned_ids))
    elif current_user.role == UserRole.HOD:
        dept_subjects_stmt = select(Subject.id).where(Subject.department_id == current_user.department_id)
        dept_subject_ids = list(db.exec(dept_subjects_stmt).all())
        base_stmt = base_stmt.where(StudentMarks.subject_id.in_(dept_subject_ids))

    if subject_id is not None:
        base_stmt = base_stmt.where(StudentMarks.subject_id == subject_id)
    if student_id is not None:
        base_stmt = base_stmt.where(StudentMarks.student_id == student_id)
    if section_id is not None:
        base_stmt = base_stmt.where(StudentMarks.section_id == section_id)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.exec(count_stmt).one()

    offset = (page - 1) * page_size
    records = db.exec(base_stmt.offset(offset).limit(page_size)).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedMarksResponse(
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
        data=[_marks_to_read(m) for m in records],
    )


@router.get(
    '/{marks_id}',
    response_model=MarksRead,
    summary='Get a single mark record by ID',
)
def get_marks(marks_id: int, db: DBSession, current_user: CurrentUser) -> MarksRead:
    marks = db.get(StudentMarks, marks_id)
    if marks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Marks record not found')
    _verify_user_subject_access(db, current_user, marks.subject_id, marks.section_id)
    return _marks_to_read(marks)


@router.delete(
    '/{marks_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a mark record (Admin only)',
)
def delete_marks(marks_id: int, db: DBSession, _admin: AdminUser) -> None:
    marks = db.get(StudentMarks, marks_id)
    if marks is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Marks record not found')
    db.delete(marks)
    db.commit()
