"""Service layer for backend utilities."""

from .auth import (
    app as auth_app,
    get_session_manager,
    get_user_repository,
    require_admin_user,
    require_authenticated_user,
    reset_auth_state,
    session_manager,
    user_repository,
)
from .storage import (
    LocalStorageService,
    S3StorageService,
    StorageConfig,
    StorageService,
    get_storage_service,
)

__all__ = [
    "StorageConfig",
    "StorageService",
    "LocalStorageService",
    "S3StorageService",
    "get_storage_service",
    "auth_app",
    "user_repository",
    "session_manager",
    "get_user_repository",
    "get_session_manager",
    "reset_auth_state",
    "require_authenticated_user",
    "require_admin_user",
]
