"""departments.py — Department management router.

Endpoints:
    POST   /departments/        — create a new department (SuperAdmin only)
    GET    /departments/        — list all departments
    GET    /departments/{id}    — retrieve a single department
    PUT    /departments/{id}    — update department details (SuperAdmin only)
    PUT    /departments/{id}/hod — assign or change HOD (SuperAdmin only)
    DELETE /departments/{id}    — delete a department (SuperAdmin only)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from app.deps import CurrentUser, DBSession, SuperAdminUser
from app.models.department import Department
from app.models.user import User, UserRole
from app.schemas.department import (
    DepartmentCreate,
    DepartmentHODAssign,
    DepartmentRead,
    DepartmentUpdate,
)

router = APIRouter(prefix='/departments', tags=['Departments'])


@router.post(
    '/',
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a new department (SuperAdmin only)',
)
def create_department(
    payload: DepartmentCreate,
    db: DBSession,
    _admin: SuperAdminUser,
) -> DepartmentRead:
    """Create a new academic department."""
    existing = db.exec(
        select(Department).where(Department.code == payload.code.upper().strip())
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Department code already exists: {payload.code}',
        )

    dept = Department(
        name=payload.name.strip(),
        code=payload.code.upper().strip(),
        hod_id=payload.hod_id,
    )

    # If hod_id is provided, verify user exists and set user role to HOD
    if payload.hod_id is not None:
        hod_user = db.get(User, payload.hod_id)
        if hod_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'User not found for hod_id: {payload.hod_id}',
            )
        hod_user.role = UserRole.HOD
        db.add(hod_user)

    db.add(dept)
    db.commit()
    db.refresh(dept)

    if dept.hod_id is not None and hod_user is not None:
        hod_user.department_id = dept.id
        db.add(hod_user)
        db.commit()

    return DepartmentRead(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        hod_id=dept.hod_id,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.get(
    '/',
    response_model=list[DepartmentRead],
    summary='List all departments',
)
def list_departments(
    db: DBSession,
    _current_user: CurrentUser,
) -> list[DepartmentRead]:
    """Return all departments."""
    depts = db.exec(select(Department)).all()
    return [
        DepartmentRead(
            id=d.id,
            name=d.name,
            code=d.code,
            hod_id=d.hod_id,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in depts
    ]


@router.get(
    '/{department_id}',
    response_model=DepartmentRead,
    summary='Get a department by ID',
)
def get_department(
    department_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> DepartmentRead:
    """Return a single department record."""
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    # If HOD or Faculty, they can only view their own department
    if current_user.role in (UserRole.HOD, UserRole.FACULTY):
        if current_user.department_id != dept.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Access restricted to your own department',
            )

    return DepartmentRead(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        hod_id=dept.hod_id,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.put(
    '/{department_id}',
    response_model=DepartmentRead,
    summary='Update department details (SuperAdmin only)',
)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: DBSession,
    _admin: SuperAdminUser,
) -> DepartmentRead:
    """Update name or code of a department."""
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    if payload.code is not None:
        code_clean = payload.code.upper().strip()
        conflict = db.exec(
            select(Department).where(
                Department.code == code_clean,
                Department.id != department_id,
            )
        ).first()
        if conflict is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f'Department code already in use: {code_clean}',
            )
        dept.code = code_clean

    if payload.name is not None:
        dept.name = payload.name.strip()

    dept.updated_at = datetime.utcnow()
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return DepartmentRead(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        hod_id=dept.hod_id,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.put(
    '/{department_id}/hod',
    response_model=DepartmentRead,
    summary='Assign or change HOD for a department (SuperAdmin only)',
)
def assign_department_hod(
    department_id: int,
    payload: DepartmentHODAssign,
    db: DBSession,
    _admin: SuperAdminUser,
) -> DepartmentRead:
    """Set the HOD user for this department and grant them HOD role."""
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    user.role = UserRole.HOD
    user.department_id = dept.id
    user.updated_at = datetime.utcnow()
    db.add(user)

    dept.hod_id = user.id
    dept.updated_at = datetime.utcnow()
    db.add(dept)

    db.commit()
    db.refresh(dept)

    return DepartmentRead(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        hod_id=dept.hod_id,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


@router.delete(
    '/{department_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a department (SuperAdmin only)',
)
def delete_department(
    department_id: int,
    db: DBSession,
    _admin: SuperAdminUser,
) -> None:
    """Permanently delete a department."""
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    db.delete(dept)
    db.commit()
