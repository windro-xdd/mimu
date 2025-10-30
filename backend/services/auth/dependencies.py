from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from .models import User
from .repository import InMemoryUserRepository
from .security import InvalidTokenError, decode_access_token
from .state import get_user_repository, get_auth_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    request: Request,
    csrf_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
    *,
    repository: InMemoryUserRepository = Depends(get_user_repository),
) -> User:
    settings = get_auth_settings()
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required.")

    try:
        payload = decode_access_token(access_token, config=settings)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    require_csrf = request.method.upper() not in SAFE_METHODS
    if require_csrf:
        csrf_cookie = request.cookies.get("csrf_token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token.")

    user_id = int(payload.get("sub", 0))
    user = repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User account is unavailable.")

    return user


def require_authenticated_user(
    request: Request,
    csrf_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
    *,
    repository: InMemoryUserRepository = Depends(get_user_repository),
) -> User:
    return get_current_user(
        request,
        csrf_header,
        repository=repository,
    )


def require_admin_user(
    request: Request,
    csrf_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
    *,
    repository: InMemoryUserRepository = Depends(get_user_repository),
) -> User:
    user = get_current_user(
        request,
        csrf_header,
        repository=repository,
    )
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin privileges are required.")
    return user
