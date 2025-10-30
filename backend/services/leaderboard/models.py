"""Dataclasses representing leaderboard entities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class UserProfile:
    """Basic user metadata used to enrich leaderboard entries."""

    user_id: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None


@dataclass(frozen=True)
class LeaderboardEntry:
    """Hydrated leaderboard entry with ranking and user metadata."""

    rank: int
    user_id: str
    value: Any
    value_field: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Serialise the entry into a JSON-compatible dictionary."""

        payload: Dict[str, Any] = {
            "rank": self.rank,
            "user_id": self.user_id,
            self.value_field: self.value,
            "username": self.username,
            "avatar_url": self.avatar_url,
        }
        return payload
