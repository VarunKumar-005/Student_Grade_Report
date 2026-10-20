"""auth.py — Authentication router.

Endpoints:
    POST /auth/login   — exchange credentials for a JWT access token
    GET  /auth/me      — return the currently authenticated user's profile
"""

from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session

from app.deps import CurrentUser, DBSession
from app.schemas.auth import CurrentUser as CurrentUserSchema
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, get_current_user_info

router = APIRouter(prefix='/auth', tags=['Auth'])


@router.post(
    '/login',
    response_model=TokenResponse,
    summary='Login with email and password',
)
def login(payload: LoginRequest, db: DBSession) -> TokenResponse:
    """Validate credentials and return a signed JWT access token."""
    try:
        return authenticate_user(db, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.get(
    '/me',
    response_model=CurrentUserSchema,
    summary='Get current authenticated user',
)
def get_me(current_user: CurrentUser) -> CurrentUserSchema:
    """Return the profile of the currently authenticated user."""
    return get_current_user_info(current_user)
