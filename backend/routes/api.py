from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.utils import secure_filename

from backend.auth import require_auth
from backend.meme_repository import MemeRepository
from backend.services.storage import StorageService

api_bp = Blueprint("api", __name__)


def _with_media_url(meme: Dict[str, Any], storage_service: StorageService) -> Dict[str, Any]:
    enriched = dict(meme)
    enriched["image_url"] = storage_service.generate_url(meme["image_key"])
    return enriched


@api_bp.route("/memes/upload", methods=["POST"])
@require_auth
def upload_meme():
    if "image" not in request.files:
        return jsonify({"error": "Image upload is required."}), 400

    image_file = request.files["image"]
    caption = (request.form.get("caption") or "").strip()

    if not caption:
        return jsonify({"error": "Caption is required."}), 400

    if image_file.filename is None or image_file.filename == "":
        return jsonify({"error": "Image filename is missing."}), 400

    storage_service: StorageService = current_app.config["STORAGE_SERVICE"]
    repository: MemeRepository = current_app.config["MEME_REPOSITORY"]

    sanitized_name = secure_filename(image_file.filename)
    extension = Path(sanitized_name).suffix if sanitized_name else ""
    file_key = f"memes/{uuid.uuid4().hex}{extension.lower()}"

    image_file.stream.seek(0)
    stored_key = storage_service.upload(
        image_file.stream,
        file_key,
        content_type=image_file.mimetype,
    )

    meme = repository.create_meme(
        user_id=g.current_user.user_id,
        caption=caption,
        image_key=stored_key,
    )

    response_payload = _with_media_url(meme, storage_service)
    return jsonify(response_payload), 201
