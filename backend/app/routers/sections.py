"""sections.py — Section (Class) and student enrollment router.

Endpoints:
    POST   /sections/                         — create a section/class (HOD / SuperAdmin)
    GET    /sections/                         — list sections (filtered by dept / semester / year)
    GET    /sections/{id}                     — retrieve a section
    PUT    /sections/{id}                     — update section details
    DELETE /sections/{id}                     — delete a section (SuperAdmin only)
    GET    /sections/{id}/students            — list students enrolled in this section
    POST   /sections/{id}/students            — enroll a single student (Faculty assigned, HOD, SuperAdmin)
    POST   /sections/{id}/students/bulk       — bulk enroll students into section (HOD, SuperAdmin)
    DELETE /sections/{id}/students/{student_id} — unenroll student from section (HOD, SuperAdmin)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.deps import CurrentUser, DBSession, FacultyUser, HODUser, SuperAdminUser
from app.models.department import Department
from app.models.faculty_subject_assignment import FacultySubjectAssignment
from app.models.section import Section, SectionStudents
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.section import (
    SectionCreate,
    SectionRead,
    SectionStudentBulkEnroll,
    SectionStudentCreateAndEnroll,
    SectionStudentEnroll,
    SectionStudentRead,
    SectionUpdate,
)

router = APIRouter(prefix='/sections', tags=['Sections & Classes'])


def _check_section_access_for_faculty(
    db: DBSession,
    section_id: int,
    user_id: int,
) -> bool:
    """Check if faculty member is assigned to teach any subject to this section."""
    assign = db.exec(
        select(FacultySubjectAssignment).where(
            FacultySubjectAssignment.section_id == section_id,
            FacultySubjectAssignment.faculty_id == user_id,
        )
    ).first()
    return assign is not None


@router.post(
    '/',
    response_model=SectionRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a new section/class (HOD or SuperAdmin)',
)
def create_section(
    payload: SectionCreate,
    db: DBSession,
    current_user: HODUser,
) -> SectionRead:
    """Create a section under a department."""
    # If HOD, verify it's for their own department
    if current_user.role == UserRole.HOD and current_user.department_id != payload.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='HOD can only create sections within their own department',
        )

    dept = db.get(Department, payload.department_id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Department not found with id: {payload.department_id}',
        )

    section = Section(
        name=payload.name.strip(),
        department_id=payload.department_id,
        semester=payload.semester,
        academic_year=payload.academic_year.strip(),
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return SectionRead(
        id=section.id,
        name=section.name,
        department_id=section.department_id,
        semester=section.semester,
        academic_year=section.academic_year,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.get(
    '/',
    response_model=list[SectionRead],
    summary='List sections/classes',
)
def list_sections(
    db: DBSession,
    current_user: FacultyUser,
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
    semester: Optional[int] = Query(default=None, description='Filter by semester'),
    academic_year: Optional[str] = Query(default=None, description='Filter by academic year'),
) -> list[SectionRead]:
    """Return sections matching filters."""
    stmt = select(Section)

    # Scoping by role
    if current_user.role == UserRole.HOD:
        stmt = stmt.where(Section.department_id == current_user.department_id)
    elif current_user.role == UserRole.FACULTY:
        # If department_id specified, allow filter; otherwise can restrict to their dept if set
        if current_user.department_id is not None and department_id is None:
            stmt = stmt.where(Section.department_id == current_user.department_id)
        elif department_id is not None:
            stmt = stmt.where(Section.department_id == department_id)
    elif department_id is not None:
        stmt = stmt.where(Section.department_id == department_id)

    if semester is not None:
        stmt = stmt.where(Section.semester == semester)
    if academic_year is not None:
        stmt = stmt.where(Section.academic_year == academic_year.strip())

    sections = db.exec(stmt).all()
    return [
        SectionRead(
            id=s.id,
            name=s.name,
            department_id=s.department_id,
            semester=s.semester,
            academic_year=s.academic_year,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sections
    ]


@router.get(
    '/{section_id}',
    response_model=SectionRead,
    summary='Get a section by ID',
)
def get_section(
    section_id: int,
    db: DBSession,
    current_user: FacultyUser,
) -> SectionRead:
    """Return a single section."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    # Access control
    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access restricted to your own department sections',
        )

    return SectionRead(
        id=section.id,
        name=section.name,
        department_id=section.department_id,
        semester=section.semester,
        academic_year=section.academic_year,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.put(
    '/{section_id}',
    response_model=SectionRead,
    summary='Update a section (HOD or SuperAdmin)',
)
def update_section(
    section_id: int,
    payload: SectionUpdate,
    db: DBSession,
    current_user: HODUser,
) -> SectionRead:
    """Update section information."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Cannot edit sections outside your department',
        )

    if payload.name is not None:
        section.name = payload.name.strip()
    if payload.semester is not None:
        section.semester = payload.semester
    if payload.academic_year is not None:
        section.academic_year = payload.academic_year.strip()
    if payload.department_id is not None:
        if current_user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Only Super Admin can change a section department',
            )
        section.department_id = payload.department_id

    section.updated_at = datetime.utcnow()
    db.add(section)
    db.commit()
    db.refresh(section)

    return SectionRead(
        id=section.id,
        name=section.name,
        department_id=section.department_id,
        semester=section.semester,
        academic_year=section.academic_year,
        created_at=section.created_at,
        updated_at=section.updated_at,
    )


@router.delete(
    '/{section_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a section (SuperAdmin only)',
)
def delete_section(
    section_id: int,
    db: DBSession,
    _admin: SuperAdminUser,
) -> None:
    """Delete a section and associated enrollments."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    # Remove section_students bridge rows first
    enrollments = db.exec(
        select(SectionStudents).where(SectionStudents.section_id == section_id)
    ).all()
    for e in enrollments:
        db.delete(e)

    db.delete(section)
    db.commit()


# ---------------------------------------------------------------------------
# Section Enrollment Endpoints
# ---------------------------------------------------------------------------


@router.get(
    '/{section_id}/students',
    response_model=list[SectionStudentRead],
    summary='List all students enrolled in a section',
)
def list_section_students(
    section_id: int,
    db: DBSession,
    current_user: FacultyUser,
) -> list[SectionStudentRead]:
    """Return all students enrolled in the specified section."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    # Verify access: SuperAdmin, HOD of this dept, or Faculty teaching this section
    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden for other departments')
    if current_user.role == UserRole.FACULTY:
        if not _check_section_access_for_faculty(db, section_id, current_user.id):
            if current_user.department_id != section.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='You are not assigned to this section',
                )

    records = db.exec(
        select(SectionStudents, Student)
        .where(SectionStudents.section_id == section_id)
        .join(Student, SectionStudents.student_id == Student.id)
    ).all()

    return [
        SectionStudentRead(
            id=sec_st.id,
            section_id=sec_st.section_id,
            student_id=st.id,
            student_name=st.name,
            student_roll=st.roll_num,
            student_reg=st.register_num,
            enrolled_at=sec_st.enrolled_at,
        )
        for sec_st, st in records
    ]


@router.post(
    '/{section_id}/students',
    response_model=SectionStudentRead,
    status_code=status.HTTP_201_CREATED,
    summary='Enroll a student into a section (Faculty assigned, HOD, SuperAdmin)',
)
def enroll_student(
    section_id: int,
    payload: SectionStudentCreateAndEnroll,
    db: DBSession,
    current_user: FacultyUser,
) -> SectionStudentRead:
    """Enroll a student into a section. If student does not exist, creates the student record first."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    # Access check: Faculty can add to their assigned section; HOD can add to their dept section; Admin can add anywhere
    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden for other departments')
    if current_user.role == UserRole.FACULTY:
        if not _check_section_access_for_faculty(db, section_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='You can only enroll students in sections assigned to you',
            )

    dept = db.get(Department, section.department_id)
    dept_code = dept.code if dept else 'DEFAULT'

    # Find or create student
    student = db.exec(
        select(Student).where(
            (Student.roll_num == payload.roll_num.strip())
            | (Student.register_num == payload.register_num.strip())
        )
    ).first()

    if student is None:
        student = Student(
            roll_num=payload.roll_num.strip(),
            register_num=payload.register_num.strip(),
            name=payload.name.strip(),
            department=dept_code,
            semester=payload.semester or section.semester,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

    # Check if already enrolled in this section
    existing_enrollment = db.exec(
        select(SectionStudents).where(
            SectionStudents.section_id == section_id,
            SectionStudents.student_id == student.id,
        )
    ).first()

    if existing_enrollment is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Student {student.roll_num} is already enrolled in this section',
        )

    enrollment = SectionStudents(section_id=section_id, student_id=student.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return SectionStudentRead(
        id=enrollment.id,
        section_id=enrollment.section_id,
        student_id=student.id,
        student_name=student.name,
        student_roll=student.roll_num,
        student_reg=student.register_num,
        enrolled_at=enrollment.enrolled_at,
    )


@router.post(
    '/{section_id}/students/bulk',
    response_model=list[SectionStudentRead],
    status_code=status.HTTP_201_CREATED,
    summary='Bulk enroll students into a section (HOD, SuperAdmin)',
)
def bulk_enroll_students(
    section_id: int,
    payload: SectionStudentBulkEnroll,
    db: DBSession,
    current_user: HODUser,
) -> list[SectionStudentRead]:
    """Bulk enroll students into a section."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden for other departments')

    dept = db.get(Department, section.department_id)
    dept_code = dept.code if dept else 'DEFAULT'

    enrolled_results: list[SectionStudentRead] = []

    for item in payload.students:
        roll = item.roll_num.strip()
        reg = item.register_num.strip()
        name = item.name.strip()

        student = db.exec(
            select(Student).where((Student.roll_num == roll) | (Student.register_num == reg))
        ).first()

        if student is None:
            student = Student(
                roll_num=roll,
                register_num=reg,
                name=name,
                department=dept_code,
                semester=item.semester or section.semester,
            )
            db.add(student)
            db.flush()

        existing = db.exec(
            select(SectionStudents).where(
                SectionStudents.section_id == section_id,
                SectionStudents.student_id == student.id,
            )
        ).first()

        if existing is None:
            enrollment = SectionStudents(section_id=section_id, student_id=student.id)
            db.add(enrollment)
            db.flush()
            enrolled_results.append(
                SectionStudentRead(
                    id=enrollment.id,
                    section_id=section_id,
                    student_id=student.id,
                    student_name=student.name,
                    student_roll=student.roll_num,
                    student_reg=student.register_num,
                    enrolled_at=enrollment.enrolled_at,
                )
            )

    db.commit()
    return enrolled_results


@router.delete(
    '/{section_id}/students/{student_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Remove student from a section (HOD, SuperAdmin)',
)
def unenroll_student(
    section_id: int,
    student_id: int,
    db: DBSession,
    current_user: HODUser,
) -> None:
    """Unenroll a student from a section."""
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')

    if current_user.role == UserRole.HOD and current_user.department_id != section.department_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Forbidden for other departments')

    enrollment = db.exec(
        select(SectionStudents).where(
            SectionStudents.section_id == section_id,
            SectionStudents.student_id == student_id,
        )
    ).first()

    if enrollment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Enrollment record not found')

    db.delete(enrollment)
    db.commit()
