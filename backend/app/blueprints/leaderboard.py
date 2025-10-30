"""Leaderboard blueprint placeholder."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("leaderboard", __name__, url_prefix="/leaderboard")

__all__ = ["bp"]
