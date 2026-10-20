"""assignments.py — Faculty-Subject-Section assignment router.

Endpoints:
    POST   /assignments/      — assign a faculty member to a subject + section (HOD / SuperAdmin)
    GET    /assignments/      — list assignments (filter by faculty/subject/section/academic_year)
    GET    /assignments/{id}  — retrieve a single assignment
    DELETE /assignments/{id}  — remove an assignment (HOD / SuperAdmin)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.deps import DBSession, FacultyUser, HODUser
from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.section import Section
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.assignment import AssignmentCreate, AssignmentRead

router = APIRouter(prefix='/assignments', tags=['Assignments'])


@router.post(
    '/',
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary='Assign a faculty member to a subject and section (HOD / SuperAdmin)',
)
def create_assignment(
    payload: AssignmentCreate,
    db: DBSession,
    current_user: HODUser,
) -> AssignmentRead:
    """Links a faculty user to a subject + section for a given academic year."""
    faculty = db.get(User, payload.faculty_id)
    if faculty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Faculty user not found with id: {payload.faculty_id}',
        )

    subject = db.get(Subject, payload.subject_id)
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Subject not found with id: {payload.subject_id}',
        )

    section = db.get(Section, payload.section_id)
    if section is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Section not found with id: {payload.section_id}',
        )

    # Scoping for HOD: can only assign within their department
    if current_user.role == UserRole.HOD:
        if subject.department_id != current_user.department_id or section.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='HOD can only assign faculty within their own department subjects and sections',
            )

    # Prevent duplicate assignment for same faculty + subject + section + academic_year
    duplicate = db.exec(
        select(FacultySubjectAssignment).where(
            FacultySubjectAssignment.faculty_id == payload.faculty_id,
            FacultySubjectAssignment.subject_id == payload.subject_id,
            FacultySubjectAssignment.section_id == payload.section_id,
            FacultySubjectAssignment.academic_year == payload.academic_year.strip(),
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Faculty is already assigned to this subject and section for the given academic year.',
        )

    assignment = FacultySubjectAssignment(
        faculty_id=payload.faculty_id,
        subject_id=payload.subject_id,
        section_id=payload.section_id,
        academic_year=payload.academic_year.strip(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return AssignmentRead(
        id=assignment.id,
        faculty_id=assignment.faculty_id,
        subject_id=assignment.subject_id,
        section_id=assignment.section_id,
        academic_year=assignment.academic_year,
    )


@router.get(
    '/',
    response_model=list[AssignmentRead],
    summary='List faculty-subject-section assignments',
)
def list_assignments(
    db: DBSession,
    _user: FacultyUser,
    faculty_id: Optional[int] = Query(default=None, description='Filter by faculty user ID'),
    subject_id: Optional[int] = Query(default=None, description='Filter by subject ID'),
    section_id: Optional[int] = Query(default=None, description='Filter by section ID'),
    academic_year: Optional[str] = Query(default=None, description='Filter by academic year'),
) -> list[AssignmentRead]:
    """Return all faculty assignments with optional filters."""
    stmt = select(FacultySubjectAssignment)
    if faculty_id is not None:
        stmt = stmt.where(FacultySubjectAssignment.faculty_id == faculty_id)
    if subject_id is not None:
        stmt = stmt.where(FacultySubjectAssignment.subject_id == subject_id)
    if section_id is not None:
        stmt = stmt.where(FacultySubjectAssignment.section_id == section_id)
    if academic_year:
        stmt = stmt.where(FacultySubjectAssignment.academic_year == academic_year.strip())

    assignments = db.exec(stmt).all()
    return [
        AssignmentRead(
            id=a.id,
            faculty_id=a.faculty_id,
            subject_id=a.subject_id,
            section_id=a.section_id,
            academic_year=a.academic_year,
        )
        for a in assignments
    ]


@router.get(
    '/{assignment_id}',
    response_model=AssignmentRead,
    summary='Get a single assignment by ID',
)
def get_assignment(
    assignment_id: int,
    db: DBSession,
    _user: FacultyUser,
) -> AssignmentRead:
    """Return a single assignment record."""
    assignment = db.get(FacultySubjectAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Assignment not found'
        )
    return AssignmentRead(
        id=assignment.id,
        faculty_id=assignment.faculty_id,
        subject_id=assignment.subject_id,
        section_id=assignment.section_id,
        academic_year=assignment.academic_year,
    )


@router.delete(
    '/{assignment_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Remove an assignment (HOD or SuperAdmin)',
)
def delete_assignment(
    assignment_id: int,
    db: DBSession,
    current_user: HODUser,
) -> None:
    """Remove a faculty-subject assignment."""
    assignment = db.get(FacultySubjectAssignment, assignment_id)
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Assignment not found'
        )

    # Scoping for HOD
    if current_user.role == UserRole.HOD:
        subject = db.get(Subject, assignment.subject_id)
        if subject and subject.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Cannot remove assignment outside your department',
            )

    db.delete(assignment)
    db.commit()
