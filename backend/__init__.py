"""Backend package exposing public APIs."""

from __future__ import annotations

from .app import create_app
from .auth import AuthenticatedUser, get_current_user, require_admin, require_auth
from .db import (
    Achievement,
    Base,
    Content,
    ContentStatus,
    ContentType,
    DatabaseConfig,
    DEFAULT_DATABASE_URL,
    User,
    UserAchievement,
    UserRole,
    Vote,
    get_engine,
    get_sessionmaker,
)
from .services.gamification import (
    GamificationConfig,
    GamificationEventResult,
    GamificationService,
    get_gamification_service,
)
from .services.storage import (
    LocalStorageService,
    S3StorageService,
    StorageConfig,
    StorageService,
    get_storage_service,
)

__all__ = [
    "Achievement",
    "AuthenticatedUser",
    "Base",
    "Content",
    "ContentStatus",
    "ContentType",
    "DatabaseConfig",
    "DEFAULT_DATABASE_URL",
    "GamificationConfig",
    "GamificationEventResult",
    "GamificationService",
    "LocalStorageService",
    "S3StorageService",
    "StorageConfig",
    "StorageService",
    "User",
    "UserAchievement",
    "UserRole",
    "Vote",
    "create_app",
    "get_current_user",
    "get_engine",
    "get_gamification_service",
    "get_sessionmaker",
    "get_storage_service",
    "require_admin",
    "require_auth",
]
