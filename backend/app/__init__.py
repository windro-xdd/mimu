"""Application factory and setup utilities for the backend service."""

from __future__ import annotations

import os
from flask import Flask

from .blueprints import register_blueprints
from .config import BaseConfig, get_config, load_environment
from .extensions import register_extensions


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure a Flask application instance."""
    # Ensure environment variables from .env are available before loading config.
    load_environment()

    resolved_name = (
        config_name
        or os.getenv("APP_CONFIG")
        or os.getenv("FLASK_ENV")
        or BaseConfig.DEFAULT_ENVIRONMENT
    )

    config_class = get_config(resolved_name)
    config_object = config_class()

    app = Flask(config_object.APP_NAME)
    app.config.from_object(config_object)
    app.config.setdefault("ENVIRONMENT", config_object.NAME)

    if hasattr(config_object, "init_app"):
        config_object.init_app(app)  # type: ignore[attr-defined]

    register_extensions(app)
    register_blueprints(app)

    return app
