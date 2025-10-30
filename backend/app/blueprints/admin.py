"""Admin blueprint for admin-related routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/", methods=["GET"])
def get_admin():
    """Get admin panel."""
    return jsonify({"message": "Admin service not yet implemented"})


__all__ = ["bp"]
