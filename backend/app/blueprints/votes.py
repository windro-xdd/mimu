"""Votes blueprint for voting-related routes."""

from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("votes", __name__, url_prefix="/votes")


@bp.route("/", methods=["GET"])
def get_votes():
    """Get votes list."""
    return jsonify({"votes": [], "message": "Votes service not yet implemented"})


__all__ = ["bp"]
