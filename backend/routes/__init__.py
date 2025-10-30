"""Application route blueprints."""

from .admin import admin_bp
from .api import api_bp

__all__ = ["admin_bp", "api_bp"]
