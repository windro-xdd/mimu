"""Configuration management for the backend Flask application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Type

ENV_FILENAMES: Iterable[str] = (".env",)


def _split_env_line(raw_line: str) -> Optional[tuple[str, str]]:
    """Parse an environment line into a key/value pair."""
    if not raw_line or raw_line.startswith("#"):
        return None

    if "=" not in raw_line:
        return None

    key, value = raw_line.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")

    if not key:
        return None

    if key.lower().startswith("export "):
        key = key.split(None, 1)[1]

    return key, value


def load_environment(env_path: Optional[Path] = None) -> Optional[Path]:
    """Load environment variables from a .env file if present."""
    candidate_files: list[Path] = []

    if env_path is not None:
        env_candidate = env_path if env_path.suffix else env_path / ".env"
        candidate_files.append(env_candidate)
    else:
        project_root = Path(__file__).resolve().parents[2]
        backend_root = project_root / "backend"
        locations = (backend_root, project_root)
        for base_path in locations:
            for filename in ENV_FILENAMES:
                candidate_files.append(base_path / filename)

    for file_path in candidate_files:
        if not file_path.exists() or not file_path.is_file():
            continue

        with file_path.open("r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                parsed = _split_env_line(raw_line.strip())
                if parsed is None:
                    continue
                key, value = parsed
                os.environ.setdefault(key, value)

        return file_path

    return None


# Load environment variables immediately so class attributes read the latest values.
load_environment()


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class BaseConfig:
    """Base configuration shared by all environments."""

    NAME = "base"
    DEFAULT_ENVIRONMENT = "development"
    DEBUG = False
    TESTING = False
    DEFAULT_DATABASE_URL = "sqlite:///../instance/app.db"

    def __init__(self) -> None:
        self.NAME = getattr(self, "NAME")
        self.DEFAULT_ENVIRONMENT = BaseConfig.DEFAULT_ENVIRONMENT
        self.APP_NAME = os.environ.get("APP_NAME", "backend")

        # Core flags
        self.DEBUG = bool(getattr(self, "DEBUG"))
        self.TESTING = bool(getattr(self, "TESTING"))

        # Secrets & security
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "development-secret-key")

        # Database configuration
        self.SQLALCHEMY_DATABASE_URI = os.environ.get(
            "DATABASE_URL",
            getattr(self, "DEFAULT_DATABASE_URL", BaseConfig.DEFAULT_DATABASE_URL),
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_ENGINE_OPTIONS: Dict[str, object] = {}

        # Alembic integration point
        self.ALEMBIC = {
            "script_location": os.environ.get("ALEMBIC_SCRIPT_LOCATION", "migrations"),
        }

        # Ancillary services
        self.REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

        # HTTP / CORS
        self.FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
        self.CORS_SUPPORTS_CREDENTIALS = True

        # JWT cookie handling
        self.JWT_COOKIE_SECURE = _env_bool("JWT_COOKIE_SECURE", default=False)
        self.JWT_COOKIE_HTTPONLY = _env_bool("JWT_COOKIE_HTTPONLY", default=True)
        self.JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")
        self.JWT_COOKIE_DOMAIN = os.environ.get("JWT_COOKIE_DOMAIN")
        self.JWT_ACCESS_COOKIE_NAME = os.environ.get("JWT_ACCESS_COOKIE_NAME", "access_token")
        self.JWT_REFRESH_COOKIE_NAME = os.environ.get(
            "JWT_REFRESH_COOKIE_NAME",
            "refresh_token",
        )
        self.JWT_ACCESS_COOKIE_PATH = os.environ.get("JWT_ACCESS_COOKIE_PATH", "/")
        self.JWT_REFRESH_COOKIE_PATH = os.environ.get("JWT_REFRESH_COOKIE_PATH", "/")
        self.JWT_SESSION_COOKIE = _env_bool("JWT_SESSION_COOKIE", default=False)

        # Healthcheck response values
        self.HEALTHCHECK_MESSAGE = os.environ.get("HEALTHCHECK_MESSAGE", "ok")
        self.HEALTHCHECK_INCLUDE_ENVIRONMENT = _env_bool(
            "HEALTHCHECK_INCLUDE_ENVIRONMENT",
            default=True,
        )

        # Server launch configuration
        self.SERVER_HOST = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
        self.SERVER_PORT = _env_int("FLASK_RUN_PORT", 5000)

    def init_app(self, app):  # pragma: no cover - hook for subclasses
        """Perform additional application setup."""
        app.config.setdefault(
            "PREFERRED_URL_SCHEME",
            os.environ.get("PREFERRED_URL_SCHEME", "http"),
        )


class DevelopmentConfig(BaseConfig):
    NAME = "development"
    DEBUG = True
    DEFAULT_DATABASE_URL = "sqlite:///../instance/dev.db"


class ProductionConfig(BaseConfig):
    NAME = "production"
    DEBUG = False

    def __init__(self) -> None:
        super().__init__()
        self.SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", default=True)


CONFIG_BY_NAME: Dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "dev": DevelopmentConfig,
    "production": ProductionConfig,
    "prod": ProductionConfig,
}


def get_config(name: str) -> Type[BaseConfig]:
    """Resolve a configuration class for the provided environment name."""
    key = name.strip().lower()
    if key in CONFIG_BY_NAME:
        return CONFIG_BY_NAME[key]

    raise ValueError(f"Unknown configuration environment: {name}")
