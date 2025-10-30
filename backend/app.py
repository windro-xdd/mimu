"""Application factory for the backend API."""

from __future__ import annotations

from typing import Optional

from flask import Flask, current_app, g
from sqlalchemy.orm import Session, sessionmaker

from .db import Base, DatabaseConfig
from .services.gamification import GamificationService, get_gamification_service
from .services.storage import get_storage_service
from .db.config import get_engine
from .routes.content import content_bp


def create_app(
    *,
    db_config: Optional[DatabaseConfig] = None,
    session_factory: Optional[sessionmaker] = None,
    gamification_service: Optional[GamificationService] = None,
) -> Flask:
    """Create and configure a Flask application instance."""

    app = Flask(__name__)

    if session_factory is None:
        resolved_config = db_config or DatabaseConfig.from_env()
        engine = get_engine(resolved_config)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    else:
        resolved_config = db_config

    app.config["DATABASE_CONFIG"] = resolved_config
    app.config["SESSION_FACTORY"] = session_factory
    app.config["GAMIFICATION_SERVICE"] = (
        gamification_service or get_gamification_service()
    )
    # Provide the storage service configuration so future routes can depend on it.
    app.config.setdefault("STORAGE_SERVICE", get_storage_service())

    @app.before_request
    def _open_session() -> None:
        factory: sessionmaker = current_app.config["SESSION_FACTORY"]
        session: Session = factory()
        g.db_session = session

    @app.teardown_request
    def _close_session(exc: Optional[BaseException]) -> None:
        session: Optional[Session] = g.pop("db_session", None)
        if session is None:
            return
        try:
            if exc is not None:
                session.rollback()
        finally:
            session.close()

    app.register_blueprint(content_bp, url_prefix="/api")

    return app


__all__ = ["create_app"]
