from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, client_ip, get_auth_service
from app.core.rate_limit import auth_rate_limit
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRefreshToken,
)

router = APIRouter(tags=["auth"])
Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/auth/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
def register(body: RegisterRequest, request: Request, svc: Service) -> UserOut:
    try:
        user = svc.register(body.email, body.password, body.full_name, client_ip(request))
    except EmailAlreadyRegistered:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from None
    return UserOut.model_validate(user)


@router.post("/auth/login", response_model=TokenPair, dependencies=[Depends(auth_rate_limit)])
def login(body: LoginRequest, request: Request, svc: Service) -> TokenPair:
    try:
        return svc.login(body.email, body.password, client_ip(request))
    except InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password") from None


@router.post("/auth/refresh", response_model=TokenPair, dependencies=[Depends(auth_rate_limit)])
def refresh(body: RefreshRequest, request: Request, svc: Service) -> TokenPair:
    try:
        return svc.refresh(body.refresh_token, client_ip(request))
    except InvalidRefreshToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, request: Request, svc: Service) -> Response:
    svc.logout(body.refresh_token, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
