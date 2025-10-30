import unittest
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from backend.services.gamification import (
    Achievement,
    GamificationConfig,
    GamificationService,
)


class FakePipeline:
    """Simple in-memory stand-in for redis pipeline semantics."""

    def __init__(self, redis: "FakeRedis") -> None:
        self._redis = redis
        self._commands: List[Tuple[str, Tuple[Any, ...], Dict[str, Any]]] = []
        self._in_multi = False

    def __enter__(self) -> "FakePipeline":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        self.reset()

    def reset(self) -> None:
        self._commands.clear()
        self._in_multi = False

    def watch(self, *keys: str) -> "FakePipeline":  # noqa: ARG002
        return self

    def multi(self) -> "FakePipeline":
        self._in_multi = True
        return self

    def _queue_command(self, name: str, *args: Any, **kwargs: Any) -> "FakePipeline":
        if not self._in_multi:
            func = getattr(self._redis, name)
            func(*args, **kwargs)
            return self
        self._commands.append((name, args, kwargs))
        return self

    def zadd(self, name: str, mapping: Dict[str, float], *args: Any, **kwargs: Any) -> "FakePipeline":
        return self._queue_command("zadd", name, mapping, *args, **kwargs)

    def zrevrange(
        self,
        name: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> "FakePipeline":
        return self._queue_command("zrevrange", name, start, end, withscores=withscores)

    def execute(self) -> Sequence[Any]:
        results: List[Any] = []
        for command, args, kwargs in self._commands:
            func = getattr(self._redis, command)
            results.append(func(*args, **kwargs))
        self.reset()
        return results


class FakeRedis:
    """Minimal Redis substitute suitable for unit testing."""

    def __init__(self) -> None:
        self.sorted_sets: Dict[str, Dict[str, float]] = {}
        self.sets: Dict[str, set[str]] = {}
        self.strings: Dict[str, int] = {}

    # Sorted set operations -------------------------------------------------
    def zincrby(self, name: str, amount: float, value: str) -> float:
        zset = self.sorted_sets.setdefault(name, {})
        zset[value] = zset.get(value, 0.0) + amount
        return zset[value]

    def zadd(self, name: str, mapping: Dict[str, float], *args: Any, **kwargs: Any) -> int:  # noqa: ARG002
        zset = self.sorted_sets.setdefault(name, {})
        added = 0
        for member, score in mapping.items():
            if member not in zset:
                added += 1
            zset[member] = float(score)
        return added

    def _sorted_members_desc(self, name: str) -> List[Tuple[str, float]]:
        zset = self.sorted_sets.get(name, {})
        return sorted(zset.items(), key=lambda item: (-item[1], item[0]))

    def zrevrange(
        self,
        name: str,
        start: int,
        end: int,
        withscores: bool = False,
    ) -> Sequence[Any]:
        members = self._sorted_members_desc(name)
        if end == -1:
            selected = members[start:]
        else:
            selected = members[start : end + 1]
        if withscores:
            return selected
        return [member for member, _ in selected]

    def zrevrank(self, name: str, value: str) -> Optional[int]:
        members = self._sorted_members_desc(name)
        for idx, (member, _) in enumerate(members):
            if member == value:
                return idx
        return None

    def zscore(self, name: str, value: str) -> Optional[float]:
        zset = self.sorted_sets.get(name, {})
        if value not in zset:
            return None
        return float(zset[value])

    # String counters ------------------------------------------------------
    def incr(self, name: str, amount: int = 1) -> int:
        value = self.strings.get(name, 0) + amount
        self.strings[name] = value
        return value

    def incrby(self, name: str, amount: int) -> int:
        return self.incr(name, amount)

    def get(self, name: str) -> Optional[int]:
        return self.strings.get(name)

    # Set operations -------------------------------------------------------
    def sadd(self, name: str, *values: str) -> int:
        members = self.sets.setdefault(name, set())
        added = 0
        for value in values:
            if value not in members:
                members.add(value)
                added += 1
        return added

    def sismember(self, name: str, value: str) -> bool:
        return value in self.sets.get(name, set())

    def smembers(self, name: str) -> Iterable[str]:
        return set(self.sets.get(name, set()))

    # Pipeline -------------------------------------------------------------
    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)


class GamificationServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.redis = FakeRedis()
        self.config = GamificationConfig()
        self.service = GamificationService(self.redis, config=self.config)

    # Vote handling -------------------------------------------------------
    def test_vote_unlocks_meme_lord(self) -> None:
        result = self.service.record_vote("user-1", 90)
        self.assertEqual(result.achievements, ())
        self.assertEqual(result.score, 90.0)

        result = self.service.record_vote("user-1", 15)
        self.assertEqual(result.score, 105.0)
        self.assertEqual(result.achievements, (Achievement.MEME_LORD,))

        # Subsequent votes should not unlock the achievement again.
        result = self.service.record_vote("user-1", 5)
        self.assertEqual(result.achievements, ())
        self.assertEqual(self.redis.zscore(self.config.score_leaderboard_key, "user-1"), 110.0)

    # Upload handling -----------------------------------------------------
    def test_first_upload_achievement_only_once(self) -> None:
        result = self.service.record_upload("creator-9", "upload-1")
        self.assertEqual(result.achievements, (Achievement.FIRST_UPLOAD,))

        result = self.service.record_upload("creator-9", "upload-2")
        self.assertEqual(result.achievements, ())
        self.assertEqual(self.redis.get(f"{self.config.upload_count_prefix}creator-9"), 2)

    # Daily visits --------------------------------------------------------
    def test_daily_visit_tracks_uniqueness(self) -> None:
        visit_day = date(2024, 1, 1)

        result = self.service.record_daily_visit("visitor-5", visit_date=visit_day)
        self.assertEqual(result.achievements, (Achievement.DAILY_VISITOR,))
        self.assertTrue(result.is_unique_daily_visit)

        result = self.service.record_daily_visit("visitor-5", visit_date=visit_day)
        self.assertEqual(result.achievements, ())
        self.assertFalse(result.is_unique_daily_visit)

        # Visiting on a new day is still tracked as unique but does not re-award the achievement.
        next_day = date(2024, 1, 2)
        result = self.service.record_daily_visit("visitor-5", visit_date=next_day)
        self.assertTrue(result.is_unique_daily_visit)
        self.assertEqual(result.achievements, ())

    # Timer submissions ---------------------------------------------------
    def test_top_timer_unlocks_when_entering_top_group(self) -> None:
        # Pre-populate nine positions so the subject lands within the top 10 when submitting.
        for idx in range(9):
            self.redis.zadd(self.config.timer_leaderboard_key, {f"speedster-{idx}": 100 - idx})

        result = self.service.record_timer_submission("challenger", 150)
        self.assertEqual(result.leaderboard_rank, 0)
        self.assertEqual(result.achievements, (Achievement.TOP_TIMER,))

        # Improved submission should not re-award the achievement but keeps the rank.
        result = self.service.record_timer_submission("challenger", 175)
        self.assertEqual(result.achievements, ())
        self.assertEqual(result.leaderboard_rank, 0)

    def test_timer_submission_outside_top_group(self) -> None:
        for idx in range(10):
            self.redis.zadd(self.config.timer_leaderboard_key, {f"top-{idx}": 500 - idx})

        result = self.service.record_timer_submission("latecomer", 10)
        self.assertEqual(result.achievements, ())
        self.assertEqual(result.leaderboard_rank, 10)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
