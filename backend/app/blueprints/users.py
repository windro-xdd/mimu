"""Users blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("users", __name__, url_prefix="/users")

__all__ = ["bp"]
