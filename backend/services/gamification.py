"""Gamification service stubs used by the API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class GamificationConfig:
    """Configuration toggle for the gamification service."""

    enabled: bool = True


@dataclass(frozen=True)
class GamificationEventResult:
    """Structured response returned by gamification events."""

    achievements: Tuple[str, ...] = ()
    score: Optional[float] = None
    leaderboard_rank: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GamificationService:
    """Very small in-memory gamification implementation.

    The real service is expected to live in a separate infrastructure
    component. For the purposes of the kata we maintain the interface and
    behave deterministically so the rest of the codebase can integrate with a
    drop-in replacement in the future.
    """

    def __init__(self, *, config: Optional[GamificationConfig] = None) -> None:
        self.config = config or GamificationConfig()
        self._scores: Dict[str, float] = {}

    def record_vote(
        self,
        user_id: str,
        delta: int,
        *,
        content_id: Optional[int] = None,
        voter_id: Optional[str] = None,
        previous_vote: Optional[int] = None,
        new_vote: Optional[int] = None,
        **_: Any,
    ) -> GamificationEventResult:
        """Record a vote delta for the specified user.

        Parameters mirror the external service contract so additional metadata
        can be provided without changing the public API of the vote endpoint.
        """

        if not self.config.enabled:
            return GamificationEventResult()

        running_total = self._scores.get(user_id, 0.0) + float(delta)
        self._scores[user_id] = running_total

        metadata = {
            "content_id": content_id,
            "voter_id": voter_id,
            "previous_vote": previous_vote,
            "new_vote": new_vote,
            "delta": delta,
        }
        # Remove unset values to keep the payload compact.
        cleaned_metadata = {key: value for key, value in metadata.items() if value is not None}

        return GamificationEventResult(score=running_total, metadata=cleaned_metadata)


def get_gamification_service(
    *, config: Optional[GamificationConfig] = None, **_: Any
) -> GamificationService:
    """Factory returning a configured :class:`GamificationService`."""

    return GamificationService(config=config)


__all__ = [
    "GamificationConfig",
    "GamificationEventResult",
    "GamificationService",
    "get_gamification_service",
]
