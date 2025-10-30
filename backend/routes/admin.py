from __future__ import annotations

from typing import Any, Dict

from flask import Blueprint, abort, current_app, jsonify, request

from backend.auth import require_admin
from backend.meme_repository import MemeRepository
from backend.services.storage import StorageService

admin_bp = Blueprint("admin", __name__)


def _with_media_url(meme: Dict[str, Any], storage_service: StorageService) -> Dict[str, Any]:
    enriched = dict(meme)
    enriched["image_url"] = storage_service.generate_url(meme["image_key"])
    return enriched


@admin_bp.route("/pending", methods=["GET"])
@require_admin
def list_pending_memes():
    storage_service: StorageService = current_app.config["STORAGE_SERVICE"]
    repository: MemeRepository = current_app.config["MEME_REPOSITORY"]
    pending_memes = repository.list_by_status("pending")
    data = [_with_media_url(meme, storage_service) for meme in pending_memes]
    return jsonify({"data": data})


@admin_bp.route("/approve/<int:meme_id>", methods=["POST"])
@require_admin
def approve_meme(meme_id: int):
    storage_service: StorageService = current_app.config["STORAGE_SERVICE"]
    repository: MemeRepository = current_app.config["MEME_REPOSITORY"]
    meme = repository.approve_meme(meme_id)
    if meme is None:
        abort(404, description="Meme not found.")
    return jsonify(_with_media_url(meme, storage_service))


@admin_bp.route("/reject/<int:meme_id>", methods=["POST"])
@require_admin
def reject_meme(meme_id: int):
    storage_service: StorageService = current_app.config["STORAGE_SERVICE"]
    repository: MemeRepository = current_app.config["MEME_REPOSITORY"]
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    reason = payload.get("reason")
    meme = repository.reject_meme(meme_id, reason=reason)
    if meme is None:
        abort(404, description="Meme not found.")
    return jsonify(_with_media_url(meme, storage_service))
