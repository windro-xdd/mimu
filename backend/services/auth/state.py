from __future__ import annotations

from .config import AuthSettings, settings
from .repository import InMemoryUserRepository
from .session import AuthSessionManager

user_repository = InMemoryUserRepository()
session_manager = AuthSessionManager(repository=user_repository, config=settings)


def get_user_repository() -> InMemoryUserRepository:
    return user_repository


def get_session_manager() -> AuthSessionManager:
    return session_manager


def get_auth_settings() -> AuthSettings:
    return settings


def reset_auth_state() -> None:
    user_repository.reset()
    session_manager.reset()
