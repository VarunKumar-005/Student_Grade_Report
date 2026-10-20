"""subjects.py — Subject management router.

Endpoints:
    POST   /subjects/      — create a new subject (HOD / SuperAdmin)
    GET    /subjects/      — list subjects (with optional department_id / semester filter)
    GET    /subjects/{id}  — retrieve a single subject
    PUT    /subjects/{id}  — update subject details (HOD / SuperAdmin)
    DELETE /subjects/{id}  — delete a subject (SuperAdmin only)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.deps import DBSession, FacultyUser, HODUser, SuperAdminUser
from app.models.department import Department
from app.models.subject import Subject
from app.models.user import UserRole
from app.schemas.subject import SubjectCreate, SubjectRead

router = APIRouter(prefix='/subjects', tags=['Subjects'])


def _resolve_dept_code(db: DBSession, department_id: int) -> str | None:
    dept = db.get(Department, department_id)
    return dept.code if dept else None


@router.post(
    '/',
    response_model=SubjectRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a new subject (HOD / SuperAdmin)',
)
def create_subject(
    payload: SubjectCreate,
    db: DBSession,
    current_user: HODUser,
) -> SubjectRead:
    """Create a new subject / course entry under a department."""
    if current_user.role == UserRole.HOD and payload.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='HOD can only create subjects in their own department',
        )

    dept = db.get(Department, payload.department_id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Department not found with id: {payload.department_id}',
        )

    existing = db.exec(
        select(Subject).where(Subject.course_code == payload.course_code.upper().strip())
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Course code already exists: {payload.course_code}',
        )

    subject = Subject(
        course_code=payload.course_code.upper().strip(),
        course_name=payload.course_name.strip(),
        department_id=payload.department_id,
        semester=payload.semester,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectRead(
        id=subject.id,
        course_code=subject.course_code,
        course_name=subject.course_name,
        department_id=subject.department_id,
        department=dept.code,
        semester=subject.semester,
    )


@router.get(
    '/',
    response_model=list[SubjectRead],
    summary='List all subjects',
)
def list_subjects(
    db: DBSession,
    _user: FacultyUser,
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
    semester: Optional[int] = Query(default=None, description='Filter by semester'),
) -> list[SubjectRead]:
    """Return all subjects, with optional department and semester filters."""
    stmt = select(Subject)
    if department_id is not None:
        stmt = stmt.where(Subject.department_id == department_id)
    if semester is not None:
        stmt = stmt.where(Subject.semester == semester)

    subjects = db.exec(stmt).all()
    # Cache department codes
    dept_map = {d.id: d.code for d in db.exec(select(Department)).all()}

    return [
        SubjectRead(
            id=s.id,
            course_code=s.course_code,
            course_name=s.course_name,
            department_id=s.department_id,
            department=dept_map.get(s.department_id),
            semester=s.semester,
        )
        for s in subjects
    ]


@router.get(
    '/{subject_id}',
    response_model=SubjectRead,
    summary='Get a subject by ID',
)
def get_subject(subject_id: int, db: DBSession, _user: FacultyUser) -> SubjectRead:
    """Return a single subject record."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')
    return SubjectRead(
        id=subject.id,
        course_code=subject.course_code,
        course_name=subject.course_name,
        department_id=subject.department_id,
        department=_resolve_dept_code(db, subject.department_id),
        semester=subject.semester,
    )


@router.put(
    '/{subject_id}',
    response_model=SubjectRead,
    summary='Update a subject (HOD / SuperAdmin)',
)
def update_subject(
    subject_id: int,
    payload: SubjectCreate,
    db: DBSession,
    current_user: HODUser,
) -> SubjectRead:
    """Update course code, name, department_id, or semester."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')

    if current_user.role == UserRole.HOD and subject.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='HOD can only update subjects in their own department',
        )

    subject.course_code = payload.course_code.upper().strip()
    subject.course_name = payload.course_name.strip()
    if payload.department_id is not None:
        subject.department_id = payload.department_id
    subject.semester = payload.semester
    subject.updated_at = datetime.utcnow()

    db.add(subject)
    db.commit()
    db.refresh(subject)
    return SubjectRead(
        id=subject.id,
        course_code=subject.course_code,
        course_name=subject.course_name,
        department_id=subject.department_id,
        department=_resolve_dept_code(db, subject.department_id),
        semester=subject.semester,
    )


@router.delete(
    '/{subject_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a subject (SuperAdmin only)',
)
def delete_subject(subject_id: int, db: DBSession, _admin: SuperAdminUser) -> None:
    """Permanently delete a subject record."""
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Subject not found')
    db.delete(subject)
    db.commit()
