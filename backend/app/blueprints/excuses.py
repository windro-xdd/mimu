"""Excuses blueprint for excuse-related routes."""

from __future__ import annotations

from flask import Blueprint, jsonify
from backend.services.excuse_api import create_excuse_app
from backend.services.excuses import get_excuse_service

bp = Blueprint("excuses", __name__, url_prefix="/excuses")


@bp.route("/", methods=["GET"])
def get_excuse():
    """Get a random excuse."""
    service = get_excuse_service()
    excuse = service.get_random_excuse()
    return jsonify({"excuse": excuse.text if excuse else "No excuses available"})


__all__ = ["bp"]
