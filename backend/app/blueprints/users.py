"""Users blueprint for user-related routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("users", __name__, url_prefix="/users")


@bp.route("/", methods=["GET"])
def get_users():
    """Get users list."""
    return jsonify({"users": [], "message": "Users service not yet implemented"})


__all__ = ["bp"]
