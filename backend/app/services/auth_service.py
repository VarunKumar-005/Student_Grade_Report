"""
auth_service.py — Business logic for authentication.

Responsibilities:
  - Validate user credentials (email + password)
  - Create new user accounts with hashed passwords
  - Issue JWT access tokens

All database mutations are committed by the *caller* (router), so this service
remains side-effect-free for easier unit testing.
"""

from sqlmodel import Session, select

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User, UserRole
from app.schemas.auth import CurrentUser, LoginRequest, TokenResponse
from app.schemas.user import UserCreate


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return db.exec(statement).first()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def authenticate_user(db: Session, payload: LoginRequest) -> TokenResponse:
    """Verify credentials and return a signed JWT.

    Raises:
        ValueError: if the email is not found or the password does not match.
    """
    user = _get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ValueError('Invalid email or password')

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


def create_user(db: Session, payload: UserCreate) -> User:
    """Create a new user row.

    The caller is responsible for committing the session.

    Raises:
        ValueError: if the email is already registered.
    """
    if _get_user_by_email(db, payload.email) is not None:
        raise ValueError(f'Email already registered: {payload.email}')

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        department_id=payload.department_id,
    )
    db.add(user)
    return user


def get_current_user_info(user: User) -> CurrentUser:
    """Map an ORM User object to the CurrentUser response schema."""
    return CurrentUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        department_id=user.department_id,
    )
