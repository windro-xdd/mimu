"""Authentication service package."""

from .app import app, get_session_manager, get_user_repository, reset_auth_state
from .dependencies import require_admin_user, require_authenticated_user
from .repository import InMemoryUserRepository
from .session import AuthSessionManager
from .state import session_manager, user_repository

__all__ = [
    "app",
    "require_authenticated_user",
    "require_admin_user",
    "AuthSessionManager",
    "InMemoryUserRepository",
    "session_manager",
    "user_repository",
    "get_session_manager",
    "get_user_repository",
    "reset_auth_state",
]
