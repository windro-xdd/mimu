from __future__ import annotations

from typing import Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status

from .dependencies import require_admin_user, require_authenticated_user
from .models import LoginRequest, RegisterRequest, User
from .repository import InMemoryUserRepository, UserAlreadyExistsError
from .security import InvalidTokenError, hash_password, verify_password
from .session import AuthSessionManager
from .state import get_session_manager, get_user_repository, reset_auth_state

app = FastAPI(title="Auth Service")


def _issue_session(
    response: Response,
    user: User,
    *,
    sessions: AuthSessionManager,
) -> Dict[str, str]:
    return sessions.establish_session(response, user)


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    response: Response,
    repository: InMemoryUserRepository = Depends(get_user_repository),
    sessions: AuthSessionManager = Depends(get_session_manager),
) -> Dict[str, object]:
    password_hash = hash_password(payload.password)
    try:
        user = repository.create_user(
            username=payload.username,
            email=payload.email,
            password_hash=password_hash,
        )
    except UserAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    token_data = _issue_session(response, user, sessions=sessions)
    return {"user": user.to_public_dict(), "csrf_token": token_data["csrf_token"]}


@app.post("/auth/login")
def login(
    payload: LoginRequest,
    response: Response,
    repository: InMemoryUserRepository = Depends(get_user_repository),
    sessions: AuthSessionManager = Depends(get_session_manager),
) -> Dict[str, object]:
    identifier = payload.identifier.lower()
    user: Optional[User]
    if "@" in identifier:
        user = repository.get_by_email(identifier)
    else:
        user = repository.get_by_username(identifier)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials.")

    token_data = _issue_session(response, user, sessions=sessions)
    return {"user": user.to_public_dict(), "csrf_token": token_data["csrf_token"]}


@app.post("/auth/logout")
def logout(  # noqa: D401 - FastAPI handles the documentation.
    request: Request,
    response: Response,
    _user: User = Depends(require_authenticated_user),
    sessions: AuthSessionManager = Depends(get_session_manager),
) -> Dict[str, str]:
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        sessions.revoke_refresh_token(refresh_token, verify_exp=False)

    sessions.clear_session(response)
    return {"detail": "Logged out."}


@app.post("/auth/refresh")
def rotate_refresh_token(
    request: Request,
    response: Response,
    sessions: AuthSessionManager = Depends(get_session_manager),
    csrf_header: Optional[str] = Header(None, alias="X-CSRF-Token"),
) -> Dict[str, object]:
    csrf_cookie = request.cookies.get("csrf_token")
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid CSRF token.")

    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token missing.")

    try:
        user, token_data = sessions.rotate_refresh_token(response, refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    return {"user": user.to_public_dict(), "csrf_token": token_data["csrf_token"]}


@app.get("/auth/me")
def read_current_user(user: User = Depends(require_authenticated_user)) -> Dict[str, object]:
    return {"user": user.to_public_dict()}


@app.get("/auth/admin")
def read_admin_user(user: User = Depends(require_admin_user)) -> Dict[str, object]:
    return {"user": user.to_public_dict()}


__all__ = [
    "app",
    "reset_auth_state",
    "get_user_repository",
    "get_session_manager",
]
