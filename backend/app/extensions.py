"""Flask extensions and integration setup."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Flask, Response
from backend.extensions import db as _db

# --- Alembic / Migrations ---------------------------------------------------
try:  # pragma: no cover
    from flask_migrate import Migrate as _Migrate  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    class _Migrate:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.app: Optional[Flask] = None
            self.db: Optional[Any] = None

        def init_app(self, app: Flask, db: Optional[Any] = None) -> None:
            self.app = app
            self.db = db

        def __repr__(self) -> str:  # pragma: no cover
            return "<MigrateStub>"


# --- CORS -------------------------------------------------------------------
try:  # pragma: no cover
    from flask_cors import CORS as _CORS  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    class _CORS:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.options: Dict[str, Any] = {}

        def init_app(self, app: Flask, *args: Any, **kwargs: Any) -> None:
            self.options.update(kwargs)
            app.extensions.setdefault("cors", self)

        def __repr__(self) -> str:  # pragma: no cover
            return "<CORSStub>"


# --- Redis ------------------------------------------------------------------
try:  # pragma: no cover
    import redis  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


migrate = _Migrate()
cors = _CORS()


class JWTCookieManager:
    """Minimal JWT cookie handling stub to centralise cookie behaviour."""

    def __init__(self) -> None:
        self.options: Dict[str, Any] = {}

    def init_app(self, app: Flask) -> None:
        self.options = {
            "secure": bool(app.config.get("JWT_COOKIE_SECURE", False)),
            "httponly": bool(app.config.get("JWT_COOKIE_HTTPONLY", True)),
            "samesite": app.config.get("JWT_COOKIE_SAMESITE", "Lax"),
            "domain": app.config.get("JWT_COOKIE_DOMAIN"),
            "access_name": app.config.get("JWT_ACCESS_COOKIE_NAME", "access_token"),
            "refresh_name": app.config.get("JWT_REFRESH_COOKIE_NAME", "refresh_token"),
            "access_path": app.config.get("JWT_ACCESS_COOKIE_PATH", "/"),
            "refresh_path": app.config.get("JWT_REFRESH_COOKIE_PATH", "/"),
            "session": bool(app.config.get("JWT_SESSION_COOKIE", False)),
        }
        app.extensions["jwt_cookies"] = self

    def set_access_cookie(
        self,
        response: Response,
        token: str,
        max_age: Optional[int] = None,
    ) -> None:
        if not self.options:
            return
        response.set_cookie(
            self.options["access_name"],
            token,
            max_age=None if self.options["session"] else max_age,
            secure=self.options["secure"],
            httponly=self.options["httponly"],
            samesite=self.options["samesite"],
            domain=self.options["domain"],
            path=self.options["access_path"],
        )

    def set_refresh_cookie(
        self,
        response: Response,
        token: str,
        max_age: Optional[int] = None,
    ) -> None:
        if not self.options:
            return
        response.set_cookie(
            self.options["refresh_name"],
            token,
            max_age=None if self.options["session"] else max_age,
            secure=self.options["secure"],
            httponly=self.options["httponly"],
            samesite=self.options["samesite"],
            domain=self.options["domain"],
            path=self.options["refresh_path"],
        )

    def clear_cookies(self, response: Response) -> None:
        if not self.options:
            return
        response.delete_cookie(
            self.options["access_name"],
            path=self.options["access_path"],
            domain=self.options["domain"],
        )
        response.delete_cookie(
            self.options["refresh_name"],
            path=self.options["refresh_path"],
            domain=self.options["domain"],
        )


jwt_manager = JWTCookieManager()
redis_client: Optional[Any] = None


def init_redis(app: Flask) -> None:
    """Initialise the Redis client and attach it to the app context."""
    global redis_client
    redis_client = None

    url = app.config.get("REDIS_URL")
    if redis is not None and url:
        try:
            redis_client = redis.from_url(url)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - network errors not exercised in tests
            redis_client = None

    app.extensions["redis_client"] = redis_client


def register_extensions(app: Flask) -> None:
    """Register all configured Flask extensions with the application."""
    _db.init_app(app)
    migrate.init_app(app, _db)
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config.get("FRONTEND_ORIGIN")}},
        supports_credentials=app.config.get("CORS_SUPPORTS_CREDENTIALS", True),
    )
    init_redis(app)
    jwt_manager.init_app(app)
