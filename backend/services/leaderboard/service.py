"""Service layer for assembling leaderboard responses."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .models import LeaderboardEntry, UserProfile

RedisMember = Union[str, bytes]
RedisScore = Union[int, float, str]

DEFAULT_SCORE_KEY = "gamification:leaderboard:score"
DEFAULT_TIMER_KEY = "gamification:leaderboard:timer"
DEFAULT_MAX_ENTRIES = 100


class LeaderboardService:
    """High-level operations for leaderboard retrieval and hydration."""

    def __init__(
        self,
        redis_client: "RedisSortedSetClient",
        user_repository: "UserRepository",
        *,
        score_key: str = DEFAULT_SCORE_KEY,
        timer_key: str = DEFAULT_TIMER_KEY,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")

        self._redis = redis_client
        self._user_repository = user_repository
        self._score_key = score_key
        self._timer_key = timer_key
        self._max_entries = max_entries

    # Public API -----------------------------------------------------------------
    def get_score_leaderboard(self, *, limit: Optional[int] = None) -> List[LeaderboardEntry]:
        """Return the score leaderboard entries sorted by highest score first."""

        resolved_limit = self._normalise_limit(limit)
        if resolved_limit == 0:
            return []

        raw_entries = self._fetch_sorted_set(
            method="zrevrange",
            key=self._score_key,
            limit=resolved_limit,
        )
        return self._hydrate_entries(raw_entries, value_field="score")

    def get_timer_leaderboard(self, *, limit: Optional[int] = None) -> List[LeaderboardEntry]:
        """Return the timer leaderboard entries sorted by fastest time first."""

        resolved_limit = self._normalise_limit(limit)
        if resolved_limit == 0:
            return []

        raw_entries = self._fetch_sorted_set(
            method="zrange",
            key=self._timer_key,
            limit=resolved_limit,
        )
        return self._hydrate_entries(raw_entries, value_field="time")

    # Internal helpers -----------------------------------------------------------
    def _normalise_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return self._max_entries

        try:
            value = int(limit)
        except (TypeError, ValueError) as exc:  # pragma: no cover - guarded upstream
            raise ValueError("limit must be an integer") from exc

        return max(0, min(value, self._max_entries))

    def _fetch_sorted_set(
        self,
        *,
        method: str,
        key: str,
        limit: int,
    ) -> Sequence[Tuple[str, Union[int, float]]]:
        if limit <= 0:
            return []

        fetcher = getattr(self._redis, method, None)
        if fetcher is None:
            raise AttributeError(f"Redis client does not support method '{method}'")

        # Redis uses inclusive end indexes; compute once for clarity.
        end_index = limit - 1
        records = fetcher(key, 0, end_index, withscores=True)
        return [
            (self._normalise_member(member), self._normalise_score(score))
            for member, score in records
        ]

    def _hydrate_entries(
        self,
        raw_entries: Sequence[Tuple[str, Union[int, float]]],
        *,
        value_field: str,
    ) -> List[LeaderboardEntry]:
        user_ids = [user_id for user_id, _ in raw_entries]
        profiles = self._user_repository.get_profiles(user_ids) if user_ids else {}

        hydrated: List[LeaderboardEntry] = []
        for index, (user_id, value) in enumerate(raw_entries, start=1):
            profile = profiles.get(user_id)
            hydrated.append(
                LeaderboardEntry(
                    rank=index,
                    user_id=user_id,
                    value=value,
                    value_field=value_field,
                    username=profile.username if profile else None,
                    avatar_url=profile.avatar_url if profile else None,
                )
            )

        return hydrated

    @staticmethod
    def _normalise_member(member: RedisMember) -> str:
        if isinstance(member, bytes):
            return member.decode("utf-8")
        return str(member)

    @staticmethod
    def _normalise_score(score: RedisScore) -> Union[int, float]:
        if isinstance(score, (int, float)):
            return int(score) if isinstance(score, float) and score.is_integer() else score

        numeric = float(score)
        return int(numeric) if numeric.is_integer() else numeric


# Protocols ---------------------------------------------------------------------

class RedisSortedSetClient:
    """Protocol-like interface describing Redis sorted set operations."""

    def zrange(
        self, key: str, start: int, end: int, *, withscores: bool = False
    ) -> Sequence[Tuple[RedisMember, RedisScore]]:  # pragma: no cover - structural typing
        raise NotImplementedError

    def zrevrange(
        self, key: str, start: int, end: int, *, withscores: bool = False
    ) -> Sequence[Tuple[RedisMember, RedisScore]]:  # pragma: no cover - structural typing
        raise NotImplementedError


class UserRepository:
    """Protocol-like interface for retrieving user profiles."""

    def get_profiles(self, user_ids: Iterable[str]) -> Dict[str, UserProfile]:  # pragma: no cover
        raise NotImplementedError
