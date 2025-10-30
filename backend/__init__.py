"""Backend package for application services."""

from .services import (
    LocalStorageService,
    S3StorageService,
    StorageConfig,
    StorageService,
    auth_app,
    get_session_manager,
    get_storage_service,
    get_user_repository,
    require_admin_user,
    require_authenticated_user,
    reset_auth_state,
    session_manager,
    user_repository,
from .services.excuse_api import ExcuseAPI, create_excuse_app
from .services.excuses import (
    DEFAULT_FIXTURE_PATH,
    ExcuseSeedConfig,
    ExcuseSeedError,
    ExcuseService,
    get_excuse_service,
)
from .services.storage import (
    StorageConfig,
    StorageService,
    LocalStorageService,
    S3StorageService,
    get_storage_service,
)

__all__ = [
    "ExcuseAPI",
    "ExcuseSeedConfig",
    "ExcuseSeedError",
    "ExcuseService",
    "DEFAULT_FIXTURE_PATH",
    "create_excuse_app",
    "get_excuse_service",
    "StorageConfig",
    "StorageService",
    "LocalStorageService",
    "S3StorageService",
    "auth_app",
    "user_repository",
    "session_manager",
    "get_user_repository",
    "get_session_manager",
    "reset_auth_state",
    "require_authenticated_user",
    "require_admin_user",
    "get_storage_service",
]
