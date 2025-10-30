"""Gamification service stubs used by API."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Protocol

try:  # pragma: no cover - optional dependency
    from redis.exceptions import WatchError  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover
    WatchError = None  # type: ignore[assignment]


class RedisPipelineProtocol(Protocol):
    """Protocol for Redis pipeline operations."""

    def execute(self) -> list:
        """Execute the pipeline and return results."""
        ...

    def __enter__(self):
        """Enter pipeline context."""
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit pipeline context."""
        ...


class RedisClientProtocol(Protocol):
    """Protocol for Redis client operations."""

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        ...

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value with optional expiration."""
        ...

    def incrby(self, key: str, amount: int) -> int:
        """Increment value by amount."""
        ...

    def zadd(self, key: str, mapping: dict, nx: bool = False) -> int:
        """Add to sorted set."""
        ...

    def zrevrange(self, key: str, start: int = 0, end: int = -1) -> list:
        """Get range from sorted set in reverse order."""
        ...

    def zscore(self, key: str, member: str) -> Optional[float]:
        """Get score of member in sorted set."""
        ...

    def pipeline(self) -> RedisPipelineProtocol:
        """Create a pipeline."""
        ...


@dataclass(frozen=True)
class GamificationConfig:
    """Configuration container for gamification service."""

    score_leaderboard_key: str = "leaderboard:score"
    timer_leaderboard_key: str = "leaderboard:timer"
    achievements_key_prefix: str = "gamification:achievements:"
    upload_count_prefix: str = "gamification:uploads:"
    upvote_total_prefix: str = "gamification:upvotes:"
    daily_visits_prefix: str = "gamification:daily-visits:"


class Achievement(str, Enum):
    """Known achievement identifiers."""

    FIRST_UPLOAD = "first_upload"
    POWER_UPLOADER = "power_uploader"
    POPULAR_CONTENT = "popular_content"
    EARLY_BIRD = "early_bird"


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
    service and communicate via Redis or HTTP. This stub exists to
    keep the API functional for development.
    """

    def __init__(self, redis_client: Optional[RedisClientProtocol] = None, *, config: Optional[GamificationConfig] = None) -> None:
        self._config = config or GamificationConfig()
        self._redis = redis_client
        self._scores: dict[str, float] = {}

    def record_vote(
        self,
        *,
        user_id: str,
        delta: int,
        content_id: Optional[int] = None,
        voter_id: Optional[str] = None,
        previous_vote: Optional[int] = None,
        new_vote: Optional[int] = None,
    ) -> GamificationEventResult:
        """Record a vote event and return gamification result."""
        # Simple in-memory implementation for development
        current_score = self._scores.get(user_id, 0.0)
        running_total = current_score + delta
        self._scores[user_id] = running_total

        metadata = {
            "content_id": content_id,
            "voter_id": voter_id,
            "previous_vote": previous_vote,
            "new_vote": new_vote,
            "delta": delta,
        }
        # Remove unset values to keep payload compact.
        cleaned_metadata = {key: value for key, value in metadata.items() if value is not None}

        return GamificationEventResult(score=running_total, metadata=cleaned_metadata)


def get_gamification_service(
    *, config: Optional[GamificationConfig] = None, **_: Any
) -> GamificationService:
    """Factory returning a configured :class:`GamificationService`."""

    return GamificationService(config=config)


__all__ = [
    "Achievement",
    "GamificationConfig",
    "GamificationEventResult",
    "GamificationService",
    "get_gamification_service",
]