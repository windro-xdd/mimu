from __future__ import annotations

from pathlib import Path
from typing import Optional

from flask import Flask

from backend.meme_repository import MemeRepository
from backend.routes.admin import admin_bp
from backend.routes.api import api_bp
from backend.services.storage import StorageConfig, StorageService, get_storage_service


def create_app(
    *,
    storage_config: Optional[StorageConfig] = None,
    storage_service: Optional[StorageService] = None,
    db_path: Optional[Path] = None,
) -> Flask:
    app = Flask(__name__)

    resolved_storage_service = storage_service or get_storage_service(storage_config)
    resolved_db_path = db_path or Path(__file__).resolve().parent / "memes.db"

    meme_repository = MemeRepository(resolved_db_path)

    app.config["STORAGE_SERVICE"] = resolved_storage_service
    app.config["MEME_REPOSITORY"] = meme_repository

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app
