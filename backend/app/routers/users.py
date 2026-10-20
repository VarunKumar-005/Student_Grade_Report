"""users.py — User management router (Hierarchical: HOD and SuperAdmin).

Endpoints:
    POST   /users/         — create a new faculty/HOD/admin account
    GET    /users/         — list user accounts (dept-scoped for HOD)
    GET    /users/{id}     — retrieve a single user by ID
    PUT    /users/{id}     — update a user
    DELETE /users/{id}     — delete a user account (SuperAdmin only)
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from app.core.security import get_password_hash
from app.deps import DBSession, HODUser, SuperAdminUser
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import create_user

router = APIRouter(prefix='/users', tags=['Users'])


@router.post(
    '/',
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary='Create a new user account (HOD / SuperAdmin)',
)
def create_user_endpoint(
    payload: UserCreate,
    db: DBSession,
    current_user: HODUser,
) -> UserRead:
    """Create a user account.
    
    - SuperAdmin can create any role (SUPER_ADMIN, HOD, FACULTY) and assign department_id.
    - HOD can only create FACULTY for their own department.
    """
    if current_user.role == UserRole.HOD:
        if payload.role not in (UserRole.FACULTY,):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='HOD can only create FACULTY accounts',
            )
        # Force department_id to HOD's department
        payload.department_id = current_user.department_id

    try:
        user = create_user(db, payload)
        db.commit()
        db.refresh(user)
        return UserRead(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            department_id=user.department_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    '/',
    response_model=list[UserRead],
    summary='List users (HOD sees dept members, SuperAdmin sees all)',
)
def list_users(
    db: DBSession,
    current_user: HODUser,
    role: Optional[UserRole] = Query(default=None, description='Filter by role'),
    department_id: Optional[int] = Query(default=None, description='Filter by department ID'),
) -> list[UserRead]:
    """Return registered users according to caller privileges."""
    stmt = select(User)
    if current_user.role == UserRole.HOD:
        stmt = stmt.where(User.department_id == current_user.department_id)
    elif department_id is not None:
        stmt = stmt.where(User.department_id == department_id)

    if role is not None:
        stmt = stmt.where(User.role == role)

    users = db.exec(stmt).all()
    return [
        UserRead(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role,
            department_id=u.department_id,
        )
        for u in users
    ]


@router.get(
    '/{user_id}',
    response_model=UserRead,
    summary='Get a user by ID',
)
def get_user(
    user_id: int,
    db: DBSession,
    current_user: HODUser,
) -> UserRead:
    """Return a single user record."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    if current_user.role == UserRole.HOD and user.department_id != current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Access restricted to your own department users',
        )

    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
    )


@router.put(
    '/{user_id}',
    response_model=UserRead,
    summary='Update a user (HOD / SuperAdmin)',
)
def update_user(
    user_id: int,
    payload: UserCreate,
    db: DBSession,
    current_user: HODUser,
) -> UserRead:
    """Update name, email, password, or role of a user account."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

    if current_user.role == UserRole.HOD:
        if user.department_id != current_user.department_id or user.role != UserRole.FACULTY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='HOD can only update faculty within their own department',
            )
        # HOD cannot change user's role or department
        payload.role = UserRole.FACULTY
        payload.department_id = current_user.department_id

    user.name = payload.name
    user.email = payload.email
    user.password_hash = get_password_hash(payload.password)
    user.role = payload.role
    if payload.department_id is not None or current_user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        user.department_id = payload.department_id
    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
    )


@router.delete(
    '/{user_id}',
    status_code=status.HTTP_204_NO_CONTENT,
    summary='Delete a user (SuperAdmin only)',
)
def delete_user(
    user_id: int,
    db: DBSession,
    _admin: SuperAdminUser,
) -> None:
    """Permanently delete a user account."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    db.delete(user)
    db.commit()
