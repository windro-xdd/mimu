"""Votes blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("votes", __name__, url_prefix="/votes")

__all__ = ["bp"]
