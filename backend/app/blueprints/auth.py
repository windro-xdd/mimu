"""Auth blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("auth", __name__, url_prefix="/auth")

__all__ = ["bp"]
