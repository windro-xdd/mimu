"""Leaderboard blueprint for leaderboard routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from backend.services.leaderboard import LeaderboardService

bp = Blueprint("leaderboard", __name__, url_prefix="/leaderboard")


@bp.route("/score", methods=["GET"])
def get_score_leaderboard():
    """Get the score leaderboard."""
    limit = request.args.get("limit", type=int)
    # For now, return a simple response
    return jsonify({"entries": [], "message": "Leaderboard service not yet implemented"})


@bp.route("/timer", methods=["GET"])
def get_timer_leaderboard():
    """Get the timer leaderboard."""
    limit = request.args.get("limit", type=int)
    # For now, return a simple response
    return jsonify({"entries": [], "message": "Leaderboard service not yet implemented"})


__all__ = ["bp"]
