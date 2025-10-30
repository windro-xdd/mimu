feat/backend-flask-scaffold-app-factory-config-blueprints-extensions
"""Backend package root exports."""

from __future__ import annotations

from .app import create_app
from .app.config import (
    BaseConfig,
    DevelopmentConfig,
    ProductionConfig,
    get_config,
    load_environment,
)
from .services.storage import (
    LocalStorageService,
    S3StorageService,

"""Backend package exposing public APIs."""

feat-leaderboards-api-score-timer-redis-hydrate
from .services.leaderboard import (
    LeaderboardAPI,
    LeaderboardEntry,
    LeaderboardService,
    UserProfile,
    create_leaderboard_api,

feature-gamification-service-redis-leaderboard-achievements
from .services.gamification import (
    Achievement,
    GamificationConfig,
    GamificationEventResult,
    GamificationService,
    get_gamification_service,
main
)
from .services.storage import (

from __future__ import annotations

from .services import (
    DEFAULT_FIXTURE_PATH,
    ExcuseAPI,
    ExcuseSeedConfig,
    ExcuseSeedError,
    ExcuseService,
    InMemoryMemesRepository,
    LocalStorageService,
    MemeCreator,
    MemeRecord,
    MemesFilter,
    MemesQueryParams,
    MemesService,
    PaginatedMemes,
    Pagination,
    RandomMemeCache,
    SQLAlchemyMemesRepository,
    S3StorageService,
main 
main
    StorageConfig,
    StorageService,
    auth_app,
    create_excuse_app,
    create_memes_app,
    get_excuse_service,
    get_memes_service,
    get_session_manager,
    get_storage_service,
feat/backend-flask-scaffold-app-factory-config-blueprints-extensions
)

__all__ = [
    "create_app",
    "BaseConfig",
    "DevelopmentConfig",
    "ProductionConfig",
    "get_config",
    "load_environment",

    get_user_repository,
    require_admin_user,
    require_authenticated_user,
    reset_auth_state,
    session_manager,
    user_repository,
)

__all__ = [
feat-leaderboards-api-score-timer-redis-hydrate
    "LeaderboardAPI",
    "LeaderboardEntry",
    "LeaderboardService",
    "UserProfile",
    "create_leaderboard_api",

feature-gamification-service-redis-leaderboard-achievements
    "Achievement",
    "GamificationConfig",
    "GamificationEventResult",
    "GamificationService",
    "get_gamification_service",
    "ExcuseAPI",
    "ExcuseSeedConfig",
    "ExcuseSeedError",
    "ExcuseService",
    "DEFAULT_FIXTURE_PATH",
    "create_excuse_app",
    "get_excuse_service",
    "MemesService",
    "MemesFilter",
    "MemesQueryParams",
    "MemeRecord",
    "MemeCreator",
    "RandomMemeCache",
    "PaginatedMemes",
    "Pagination",
    "InMemoryMemesRepository",
    "SQLAlchemyMemesRepository",
    "create_memes_app",
    "get_memes_service",
main
main
main
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
