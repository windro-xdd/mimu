"""Health check blueprint."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__, url_prefix="/health")


@bp.route("/", methods=["GET"], strict_slashes=False)
def healthcheck():
    """Return a minimal application health payload."""
    message = current_app.config.get("HEALTHCHECK_MESSAGE", "ok")
    payload = {"status": message}

    if current_app.config.get("HEALTHCHECK_INCLUDE_ENVIRONMENT", True):
        payload["environment"] = current_app.config.get("ENVIRONMENT", "unknown")

    return jsonify(payload)


__all__ = ["bp"]
