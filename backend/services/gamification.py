feature-gamification-service-redis-leaderboard-achievements
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Iterable, Optional, Protocol, Sequence, Tuple, Union

try:  # pragma: no cover - optional dependency
    from redis.exceptions import WatchError  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    class WatchError(RuntimeError):
        """Fallback WatchError used when redis package is not installed."""


class RedisPipelineProtocol(Protocol):
    """Subset of Redis pipeline features exercised by the gamification service."""

    def __enter__(self) -> "RedisPipelineProtocol":
        ...

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        ...

    def watch(self, *keys: str) -> "RedisPipelineProtocol":
        ...

    def multi(self) -> "RedisPipelineProtocol":
        ...

    def zadd(self, name: str, mapping: MappingType, *args: Any, **kwargs: Any) -> "RedisPipelineProtocol":
        ...

    def zrevrange(
        self,
        name: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> "RedisPipelineProtocol":
        ...

    def execute(self) -> Sequence[Any]:
        ...


MappingType = Union[Sequence[Tuple[str, Union[int, float]]], dict[str, Union[int, float]]]


class RedisClientProtocol(Protocol):
    """Protocol describing the Redis operations used by the service."""

    def zincrby(self, name: str, amount: float, value: str) -> float:
        ...

    def zadd(self, name: str, mapping: MappingType, *args: Any, **kwargs: Any) -> int:
        ...

    def zrevrange(
        self,
        name: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> Sequence[Any]:
        ...

    def zrevrank(self, name: str, value: str) -> Optional[int]:
        ...

    def zscore(self, name: str, value: str) -> Optional[float]:  # pragma: no cover - helper
        ...

    def sadd(self, name: str, *values: str) -> int:
        ...

    def sismember(self, name: str, value: str) -> bool:  # pragma: no cover - helper
        ...

    def smembers(self, name: str) -> Iterable[Any]:
        ...

    def incr(self, name: str, amount: int = 1) -> int:
        ...

    def incrby(self, name: str, amount: int) -> int:
        ...

    def get(self, name: str) -> Optional[Any]:  # pragma: no cover - helper
        ...

    def pipeline(self) -> RedisPipelineProtocol:
        ...

"""Gamification service stubs used by the API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
 main


@dataclass(frozen=True)
class GamificationConfig:
feature-gamification-service-redis-leaderboard-achievements
    """Configuration container for the gamification service."""

    score_leaderboard_key: str = "leaderboard:score"
    timer_leaderboard_key: str = "leaderboard:timer"
    achievements_key_prefix: str = "gamification:achievements:"
    upload_count_prefix: str = "gamification:uploads:"
    upvote_total_prefix: str = "gamification:upvotes:"
    daily_visits_prefix: str = "gamification:daily-visits:"
    timer_top_n: int = 10
    meme_lord_threshold: int = 100
    redis_url: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timer_top_n < 1:
            raise ValueError("timer_top_n must be at least 1")
        if self.meme_lord_threshold < 1:
            raise ValueError("meme_lord_threshold must be a positive integer")


class Achievement(str, Enum):
    """Enumeration of supported achievement codes."""

    FIRST_UPLOAD = "first_upload"
    MEME_LORD = "meme_lord"
    DAILY_VISITOR = "daily_visitor"
    TOP_TIMER = "top_timer"

    """Configuration toggle for the gamification service."""

    enabled: bool = True
main


@dataclass(frozen=True)
class GamificationEventResult:
feature-gamification-service-redis-leaderboard-achievements
    """Structured response describing the outcome of an event."""

    achievements: Tuple[Achievement, ...] = ()
    score: Optional[float] = None
    leaderboard_rank: Optional[int] = None
    is_unique_daily_visit: Optional[bool] = None


class GamificationService:
    """Coordinate score tracking, leaderboards, and achievement unlocks."""

    def __init__(
        self,
        redis_client: RedisClientProtocol,
        *,
        config: Optional[GamificationConfig] = None,
    ) -> None:
        self.redis = redis_client
        self.config = config or GamificationConfig()

    # Public API -----------------------------------------------------------
    def adjust_score(self, user_id: str, delta: Union[int, float]) -> float:
        """Adjust the user's score and return their updated total."""

        return float(
            self.redis.zincrby(
                self.config.score_leaderboard_key,
                float(delta),
                user_id,
            )
        )

    def record_vote(self, user_id: str, delta: int) -> GamificationEventResult:
        """Register an upvote/downvote event and evaluate achievements."""

        new_score = self.adjust_score(user_id, delta)
        total_upvotes = int(self.redis.incrby(self._upvote_total_key(user_id), delta))

        achievements: list[Achievement] = []
        if total_upvotes >= self.config.meme_lord_threshold:
            if self._unlock_achievement(user_id, Achievement.MEME_LORD):
                achievements.append(Achievement.MEME_LORD)

        return GamificationEventResult(achievements=tuple(achievements), score=new_score)

    def record_upload(self, user_id: str, upload_id: str) -> GamificationEventResult:  # noqa: ARG002
        """Handle a new upload and unlock the first-upload achievement."""

        upload_count = int(self.redis.incr(self._upload_count_key(user_id), 1))

        achievements: list[Achievement] = []
        if upload_count == 1:
            if self._unlock_achievement(user_id, Achievement.FIRST_UPLOAD):
                achievements.append(Achievement.FIRST_UPLOAD)

        return GamificationEventResult(achievements=tuple(achievements))

    def record_daily_visit(
        self,
        user_id: str,
        *,
        visit_date: Optional[date] = None,
    ) -> GamificationEventResult:
        """Track a user's daily visit and unlock the daily-visitor achievement."""

        current_date = visit_date or date.today()
        daily_key = f"{self.config.daily_visits_prefix}{current_date.isoformat()}"
        unique_visit = bool(self.redis.sadd(daily_key, user_id))

        achievements: list[Achievement] = []
        if unique_visit:
            if self._unlock_achievement(user_id, Achievement.DAILY_VISITOR):
                achievements.append(Achievement.DAILY_VISITOR)

        return GamificationEventResult(
            achievements=tuple(achievements),
            is_unique_daily_visit=unique_visit,
        )

    def record_timer_submission(
        self,
        user_id: str,
        timer_value: Union[int, float],
    ) -> GamificationEventResult:
        """Record a timer submission and evaluate the top-timer achievement."""

        timer_key = self.config.timer_leaderboard_key
        achievements: list[Achievement] = []

        with self.redis.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(timer_key)
                    pipe.multi()
                    pipe.zadd(timer_key, {user_id: float(timer_value)})
                    pipe.zrevrange(timer_key, 0, self.config.timer_top_n - 1)
                    results = pipe.execute()
                    top_members = [self._ensure_str(value) for value in results[1]]
                    break
                except WatchError:
                    continue

        in_top_group = user_id in top_members
        if in_top_group:
            if self._unlock_achievement(user_id, Achievement.TOP_TIMER):
                achievements.append(Achievement.TOP_TIMER)

        rank = self.redis.zrevrank(timer_key, user_id)
        return GamificationEventResult(
            achievements=tuple(achievements),
            leaderboard_rank=rank,
        )

    def list_achievements(self, user_id: str) -> Tuple[Achievement, ...]:
        """Return a deterministic tuple of unlocked achievements for the user."""

        raw_values = self.redis.smembers(self._achievements_key(user_id))
        collected: set[Achievement] = set()
        for value in raw_values:
            as_str = self._ensure_str(value)
            try:
                collected.add(Achievement(as_str))
            except ValueError:  # Unknown achievement stored externally
                continue
        return tuple(sorted(collected, key=lambda item: item.value))

    # Internal helpers -----------------------------------------------------
    def _achievements_key(self, user_id: str) -> str:
        return f"{self.config.achievements_key_prefix}{user_id}"

    def _upload_count_key(self, user_id: str) -> str:
        return f"{self.config.upload_count_prefix}{user_id}"

    def _upvote_total_key(self, user_id: str) -> str:
        return f"{self.config.upvote_total_prefix}{user_id}"

    def _unlock_achievement(self, user_id: str, achievement: Achievement) -> bool:
        key = self._achievements_key(user_id)
        added = self.redis.sadd(key, achievement.value)
        return bool(added)

    @staticmethod
    def _ensure_str(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)


def get_gamification_service(
    *,
    redis_client: Optional[RedisClientProtocol] = None,
    config: Optional[GamificationConfig] = None,
    **redis_kwargs: Any,
) -> GamificationService:
    """Factory that returns a configured :class:`GamificationService`."""

    resolved_config = config or GamificationConfig()

    if redis_client is None:
        try:  # pragma: no cover - optional dependency
            import redis  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "redis_client must be provided when the redis package is unavailable."
            ) from exc

        redis_url = resolved_config.redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = redis.Redis.from_url(redis_url, decode_responses=True, **redis_kwargs)

    return GamificationService(redis_client=redis_client, config=resolved_config)


__all__ = [
    "Achievement",

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
main
    "GamificationConfig",
    "GamificationEventResult",
    "GamificationService",
    "get_gamification_service",
]
