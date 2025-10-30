"""Admin blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/admin")

__all__ = ["bp"]
