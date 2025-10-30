"""Content-related API routes."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint, abort, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.auth import require_auth
from backend.models import Content, Vote
from backend.services.gamification import GamificationEventResult

content_bp = Blueprint("content", __name__)

_ALLOWED_VOTES: Dict[str, int] = {"up": 1, "down": -1, "neutral": 0}
_VALUE_TO_LABEL = {value: key for key, value in _ALLOWED_VOTES.items()}


def _get_session() -> Session:
    session = getattr(g, "db_session", None)
    if session is None:
        raise RuntimeError("Database session is not available for this request.")
    return session


@content_bp.route("/content/<int:content_id>/vote", methods=["POST"])
@require_auth
def vote_on_content(content_id: int):
    """Record or update a user's vote for a piece of content."""

    payload = request.get_json(silent=True) or {}
    vote_token = str(payload.get("vote", "")).lower()
    if vote_token not in _ALLOWED_VOTES:
        return (
            jsonify({"error": "vote must be one of: up, down, neutral."}),
            400,
        )

    new_value = _ALLOWED_VOTES[vote_token]
    session = _get_session()

    content = session.get(Content, content_id)
    if content is None:
        abort(404, description="Content not found.")

    try:
        voter_id = int(getattr(g.current_user, "user_id"))
    except (TypeError, ValueError, AttributeError):
        abort(400, description="Authenticated user id must be an integer.")

    previous_vote = session.get(Vote, (voter_id, content_id))
    previous_value = previous_vote.value if previous_vote is not None else 0
    delta = new_value - previous_value

    # Idempotent behaviour: when the incoming vote matches the persisted one we
    # simply return the latest aggregate numbers without making any changes.
    if delta == 0:
        session.refresh(content)
        session.refresh(content.author)
        response_payload = _build_vote_response(content, new_value, None)
        return jsonify(response_payload)

    try:
        with session.begin():
            if new_value == 0:
                if previous_vote is not None:
                    session.delete(previous_vote)
            else:
                if previous_vote is None:
                    session.add(
                        Vote(user_id=voter_id, content_id=content_id, value=new_value)
                    )
                else:
                    previous_vote.value = new_value

            _apply_vote_delta(content, previous_value, new_value, delta)
            session.flush()
            session.refresh(content)
            session.refresh(content.author)
    except SQLAlchemyError:  # pragma: no cover - defensive double check
        session.rollback()
        abort(500, description="Unable to process vote at this time.")

    gamification_result: Optional[GamificationEventResult] = None
    service = current_app.config.get("GAMIFICATION_SERVICE")
    if service is not None and delta != 0:
        gamification_result = service.record_vote(
            user_id=str(content.author_id),
            delta=delta,
            content_id=content.id,
            voter_id=str(voter_id),
            previous_vote=previous_value,
            new_vote=new_value,
        )

    response_payload = _build_vote_response(content, new_value, gamification_result)
    return jsonify(response_payload)


def _apply_vote_delta(
    content: Content, previous_value: int, new_value: int, delta: int
) -> None:
    """Mutate aggregate counters on the content and author objects."""

    content.score = int((content.score or 0) + delta)

    if previous_value == 1:
        content.upvotes = max(0, int(content.upvotes or 0) - 1)
    elif previous_value == -1:
        content.downvotes = max(0, int(content.downvotes or 0) - 1)

    if new_value == 1:
        content.upvotes = int(content.upvotes or 0) + 1
    elif new_value == -1:
        content.downvotes = int(content.downvotes or 0) + 1

    author = content.author
    author.total_score = int((author.total_score or 0) + delta)


def _build_vote_response(
    content: Content,
    user_vote: int,
    gamification_result: Optional[GamificationEventResult],
) -> Dict[str, Any]:
    """Serialise the response payload returned by the vote endpoint."""

    payload: Dict[str, Any] = {
        "content_id": content.id,
        "score": {
            "total": int(content.score or 0),
            "upvotes": int(content.upvotes or 0),
            "downvotes": int(content.downvotes or 0),
        },
        "user_vote": _VALUE_TO_LABEL.get(user_vote, "neutral"),
        "creator": {
            "id": content.author_id,
            "total_score": int(content.author.total_score or 0),
        },
    }

    if gamification_result is not None:
        payload["gamification"] = _serialise_gamification_result(gamification_result)

    return payload


def _serialise_gamification_result(result: GamificationEventResult) -> Dict[str, Any]:
    """Convert a :class:`GamificationEventResult` into JSON-ready data."""

    achievements = []
    for achievement in result.achievements:
        if hasattr(achievement, "value"):
            achievements.append(getattr(achievement, "value"))
        else:
            achievements.append(str(achievement))

    payload: Dict[str, Any] = {}
    if achievements:
        payload["achievements"] = achievements
    if result.score is not None:
        payload["score"] = result.score
    if result.leaderboard_rank is not None:
        payload["leaderboard_rank"] = result.leaderboard_rank

    metadata = getattr(result, "metadata", None)
    if metadata:
        payload["metadata"] = metadata

    # Some implementations expose this flag – include it when available.
    is_unique = getattr(result, "is_unique_daily_visit", None)
    if is_unique is not None:
        payload["is_unique_daily_visit"] = is_unique

    return payload


__all__ = ["content_bp", "vote_on_content"]
