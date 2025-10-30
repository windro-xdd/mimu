"""Service layer for backend utilities."""

from .excuse_api import ExcuseAPI, create_excuse_app
from .excuses import (
    DEFAULT_FIXTURE_PATH,
    ExcuseSeedConfig,
    ExcuseSeedError,
    ExcuseService,
    get_excuse_service,
)
from .storage import (
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
    "get_storage_service",
]
