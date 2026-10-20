"""students.py — Student management router (Admin only for write, Faculty for read).

Endpoints:
    POST   /students/       — create a new student
    GET    /students/       — list all students (with optional filters)
    GET    /students/{id}   — retrieve a single student
    PUT    /students/{id}   — update student details
    DELETE /students/{id}   — delete a student
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.deps import AdminUser, DBSession, FacultyUser, HODUser, SuperAdminUser
from app.models.department import Department
from app.models.student import Student
from app.models.user import UserRole
from app.schemas.student import StudentCreate, StudentRead

router = APIRouter(prefix='/students', tags=['Students'])


@router.post(
    '/',
    response_model=StudentRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a new student (HOD / SuperAdmin)',
)
def create_student(
    payload: StudentCreate,
    db: DBSession,
    current_user: HODUser,
) -> StudentRead:
    """Add a new student to the system."""
    if current_user.role == UserRole.HOD and current_user.department_id is not None:
        dept = db.get(Department, current_user.department_id)
        if dept and payload.department != dept.code:
            payload.department = dept.code
    # Uniqueness checks
    roll_conflict = db.exec(
        select(Student).where(Student.roll_num == payload.roll_num)
    ).first()
    if roll_conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Roll number already exists: {payload.roll_num}',
        )
    reg_conflict = db.exec(
        select(Student).where(Student.register_num == payload.register_num)
    ).first()
    if reg_conflict is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Register number already exists: {payload.register_num}',
        )

    student = Student(
        roll_num=payload.roll_num,
        register_num=payload.register_num,
        name=payload.name,
        department=payload.department,
        semester=payload.semester,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentRead(
        id=student.id,
        roll_num=student.roll_num,
        register_num=student.register_num,
        name=student.name,
        department=student.department,
        semester=student.semester,
    )


@router.get(
    '/',
    response_model=list[StudentRead],
    summary='List all students',
)
def list_students(
    db: DBSession,
    _user: FacultyUser,
    department: str | None = Query(default=None, description='Filter by department'),
    semester: int | None = Query(default=None, description='Filter by semester'),
) -> list[StudentRead]:
    """Return all students, with optional department and semester filters."""
    stmt = select(Student)
    if department:
        stmt = stmt.where(Student.department == department)
    if semester is not None:
        stmt = stmt.where(Student.semester == semester)

    students = db.exec(stmt).all()
    return [
        StudentRead(
            id=s.id,
            roll_num=s.roll_num,
            register_num=s.register_num,
            name=s.name,
            department=s.department,
            semester=s.semester,
        )
        for s in students
    ]


@router.get(
    '/{student_id}',
    response_model=StudentRead,
    summary='Get a student by ID',
)
def get_student(student_id: int, db: DBSession, _user: FacultyUser) -> StudentRead:
    """Return a single student record."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Student not found')
    return StudentRead(
        id=student.id,
        roll_num=student.roll_num,
        register_num=student.register_num,
        name=student.name,
        department=student.department,
        semester=student.semester,
    )


@router.put(
    '/{student_id}',
    response_model=StudentRead,
    summary='Update a student (HOD / SuperAdmin)',
)
def update_student(
    student_id: int,
    payload: StudentCreate,
    db: DBSession,
    current_user: HODUser,
) -> StudentRead:
    """Update student identity fields."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Student not found')

    if current_user.role == UserRole.HOD and current_user.department_id is not None:
        dept = db.get(Department, current_user.department_id)
        if dept and student.department != dept.code:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='HOD can only update students within their department',
            )

    student.roll_num = payload.roll_num
    student.register_num = payload.register_num
    student.name = payload.name
    student.department = payload.department
    student.semester = payload.semester
    student.updated_at = datetime.utcnow()
    db.add(student)
    db.commit()
    db.refresh(student)
    return StudentRead(
        id=student.id,
        roll_num=student.roll_num,
        register_num=student.register_num,
        name=student.name,
        department=student.department,
        semester=student.semester,
    )


@router.delete(
    '/{student_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a student (Admin)',
)
def delete_student(student_id: int, db: DBSession, _admin: AdminUser) -> None:
    """Permanently delete a student record."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Student not found')
    db.delete(student)
    db.commit()
