"""Content blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("content", __name__, url_prefix="/content")

__all__ = ["bp"]
