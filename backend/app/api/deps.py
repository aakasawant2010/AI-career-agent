from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

DbSession = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_current_user(
    db: DbSession,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        user_id = decode_access_token(creds.credentials)
    except (jwt.PyJWTError, ValueError):
        raise unauthorized from None
    user = UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
