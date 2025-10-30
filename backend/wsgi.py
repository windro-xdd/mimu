"""WSGI entrypoint for running the backend service."""

from __future__ import annotations

from backend.app import create_app
from backend.app.config import load_environment

load_environment()
app = create_app()

__all__ = ["app"]
