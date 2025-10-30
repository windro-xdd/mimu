"""Lightweight authentication helpers for the Flask API."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from flask import abort, g, request


@dataclass
class AuthenticatedUser:
    """Representation of the authenticated principal."""

    user_id: str
    role: str = "user"


F = TypeVar("F", bound=Callable[..., Any])


def get_current_user() -> Optional[AuthenticatedUser]:
    """Extract the current user from standard auth headers."""

    user_id = request.headers.get("X-User-Id")
    if not user_id:
        return None

    role = request.headers.get("X-User-Role", "user").lower()
    return AuthenticatedUser(user_id=user_id, role=role)


def require_auth(func: F) -> F:
    """Route decorator enforcing authentication."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        user = get_current_user()
        if user is None:
            abort(401, description="Authentication required.")
        g.current_user = user
        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_admin(func: F) -> F:
    """Route decorator enforcing administrator role."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        user = get_current_user()
        if user is None:
            abort(401, description="Authentication required.")
        if user.role != "admin":
            abort(403, description="Admin privileges required.")
        g.current_user = user
        return func(*args, **kwargs)

    return cast(F, wrapper)


__all__ = ["AuthenticatedUser", "get_current_user", "require_admin", "require_auth"]
