"""
deps.py — Shared FastAPI dependency injection.

Provides:
  - get_db          : yields an active SQLModel Session
  - get_current_user: decodes the Bearer JWT and returns the authenticated User
  - require_admin   : asserts the authenticated user holds the ADMIN role
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.core.security import decode_access_token
from app.database import get_session
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


def get_db() -> Session:
    """Yield an SQLModel Session (FastAPI dependency)."""
    yield from get_session()


DBSession = Annotated[Session, Depends(get_db)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> User:
    """Decode JWT Bearer token and return the corresponding User row.

    Raises 401 if the token is missing, invalid, or the user no longer exists.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str | None = payload.get('sub')
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except (ValueError, KeyError):
        raise credentials_exception

    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------------------------------------------------------------------
# Role guards (Hierarchical: SUPER_ADMIN / ADMIN > HOD > FACULTY)
# ---------------------------------------------------------------------------


def require_super_admin(current_user: CurrentUser) -> User:
    """Dependency that allows access only to SUPER_ADMIN (or legacy ADMIN)."""
    if current_user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Super Administrator access required',
        )
    return current_user


def require_hod(current_user: CurrentUser) -> User:
    """Dependency that allows access to HOD, SUPER_ADMIN, and ADMIN users."""
    if current_user.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.HOD):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Head of Department (HOD) or Administrator access required',
        )
    return current_user


def require_admin(current_user: CurrentUser) -> User:
    """Alias for require_super_admin for backward compatibility."""
    return require_super_admin(current_user)


def require_faculty(current_user: CurrentUser) -> User:
    """Dependency that allows access to FACULTY, HOD, and Administrators."""
    if current_user.role not in (
        UserRole.FACULTY,
        UserRole.HOD,
        UserRole.SUPER_ADMIN,
        UserRole.ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Faculty, HOD, or Administrator access required',
        )
    return current_user


SuperAdminUser = Annotated[User, Depends(require_super_admin)]
HODUser = Annotated[User, Depends(require_hod)]
AdminUser = Annotated[User, Depends(require_admin)]
FacultyUser = Annotated[User, Depends(require_faculty)]
