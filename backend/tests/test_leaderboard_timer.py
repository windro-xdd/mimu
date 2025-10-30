import math
import unittest
from typing import Dict, List, Optional

from backend.services.leaderboard import (
    GamificationService,
    RedisRateLimiter,
    TimerLeaderboardAPI,
    TimerLeaderboardService,
    TimerTokenSigner,
)


class FakeClock:
    def __init__(self, start_seconds: float = 0.0) -> None:
        self._current = float(start_seconds)

    def now(self) -> float:
        return self._current

    def millis(self) -> int:
        return int(self._current * 1000)

    def advance(self, seconds: float) -> None:
        self._current += seconds


class InMemoryRedis:
    """Minimal in-memory redis substitute for tests."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self._kv: Dict[str, int] = {}
        self._expires: Dict[str, float] = {}
        self._zsets: Dict[str, Dict[str, float]] = {}

    # Rate limiting operations -------------------------------------------------
    def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        value = self._kv.get(key, 0) + 1
        self._kv[key] = value
        return value

    def expire(self, key: str, ttl_seconds: int) -> None:
        if key in self._kv:
            self._expires[key] = self._clock.now() + ttl_seconds

    def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._kv:
            return -2
        expires_at = self._expires.get(key)
        if expires_at is None:
            return -1
        seconds_left = expires_at - self._clock.now()
        if seconds_left <= 0:
            self._kv.pop(key, None)
            self._expires.pop(key, None)
            return -2
        return max(0, int(math.ceil(seconds_left)))

    # Sorted set operations ----------------------------------------------------
    def zscore(self, name: str, member: str) -> Optional[float]:
        return self._zsets.get(name, {}).get(member)

    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        zset = self._zsets.setdefault(name, {})
        added = 0
        for member, score in mapping.items():
            if member not in zset:
                added += 1
            zset[member] = float(score)
        return added

    def zrank(self, name: str, member: str) -> Optional[int]:
        zset = self._zsets.get(name)
        if not zset or member not in zset:
            return None
        sorted_members = sorted(zset.items(), key=lambda item: (item[1], item[0]))
        for index, (candidate, _) in enumerate(sorted_members):
            if candidate == member:
                return index
        return None

    def zcard(self, name: str) -> int:
        return len(self._zsets.get(name, {}))

    def _purge_if_expired(self, key: str) -> None:
        expires_at = self._expires.get(key)
        if expires_at is not None and self._clock.now() >= expires_at:
            self._kv.pop(key, None)
            self._expires.pop(key, None)


class FakeGamification(GamificationService):
    def __init__(self) -> None:
        self.events: List[Dict[str, int]] = []

    def trigger_top_timer(self, user_id: str, rank: int, time_ms: int) -> None:
        self.events.append({"user_id": user_id, "rank": rank, "time_ms": time_ms})


class FakeSummaryRepository:
    def __init__(self) -> None:
        self.records: List[Dict[str, Optional[int]]] = []

    def record_personal_best(
        self, user_id: str, time_ms: int, started_at_ms: int, rank: Optional[int]
    ) -> None:
        self.records.append(
            {
                "user_id": user_id,
                "time_ms": time_ms,
                "started_at_ms": started_at_ms,
                "rank": rank,
            }
        )


class TimerLeaderboardServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock(start_seconds=1_700_000_000.0)
        self.redis = InMemoryRedis(self.clock)
        self.signer = TimerTokenSigner(
            "super-secret", now_provider=self.clock.millis
        )
        self.gamification = FakeGamification()
        self.rate_limiter = RedisRateLimiter(
            self.redis, max_attempts=2, window_seconds=60
        )
        self.service = TimerLeaderboardService(
            self.redis,
            self.signer,
            gamification_service=self.gamification,
            rate_limiter=self.rate_limiter,
        )
        self.api = TimerLeaderboardAPI(self.service)

    # Helpers -----------------------------------------------------------------
    def _payload_for(self, user_id: str, time_ms: int) -> Dict[str, int]:
        started_at = self.clock.millis()
        token = self.signer.issue_token(user_id, started_at)
        return {
            "time_ms": time_ms,
            "started_at_ms": started_at,
            "token": token,
        }

    # Tests -------------------------------------------------------------------
    def test_valid_submission_updates_leaderboard(self) -> None:
        payload = self._payload_for("user-1", time_ms=62_345)
        status, body = self.api.post_timer("user-1", payload)

        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "accepted")
        self.assertTrue(body["personalBest"])
        self.assertEqual(body["bestTimeMs"], 62_345)
        self.assertEqual(body["rank"], 1)
        self.assertTrue(body["topTen"])
        self.assertEqual(
            self.gamification.events,
            [{"user_id": "user-1", "rank": 1, "time_ms": 62_345}],
        )

    def test_invalid_token_rejected(self) -> None:
        payload = {
            "time_ms": 70_000,
            "started_at_ms": self.clock.millis(),
            "token": "invalid",
        }
        status, body = self.api.post_timer("user-1", payload)

        self.assertEqual(status, 400)
        self.assertEqual(body["status"], "invalid_token")
        self.assertIn("detail", body)
        self.assertEqual(self.redis.zcard("leaderboard:timer"), 0)

    def test_rate_limit_enforced(self) -> None:
        first = self._payload_for("user-1", time_ms=60_000)
        self.assertEqual(self.api.post_timer("user-1", first)[0], 200)

        second = self._payload_for("user-1", time_ms=59_500)
        self.assertEqual(self.api.post_timer("user-1", second)[0], 200)

        third = self._payload_for("user-1", time_ms=59_000)
        status, body = self.api.post_timer("user-1", third)
        self.assertEqual(status, 429)
        self.assertEqual(body["status"], "rate_limited")
        self.assertEqual(body["attemptsRemaining"], 0)
        self.assertGreater(body["retryAfterSeconds"], 0)

    def test_top_ten_gamification_triggers_on_entry_only(self) -> None:
        for index in range(9):
            self.redis.zadd(
                "leaderboard:timer", {f"other-{index}": float(80_000 + index)}
            )

        first = self._payload_for("contender", time_ms=79_000)
        status, body = self.api.post_timer("contender", first)
        self.assertEqual(status, 200)
        self.assertEqual(body["rank"], 1)
        self.assertEqual(len(self.gamification.events), 1)

        improved = self._payload_for("contender", time_ms=78_500)
        status, body = self.api.post_timer("contender", improved)
        self.assertEqual(status, 200)
        self.assertEqual(body["rank"], 1)
        self.assertEqual(body["bestTimeMs"], 78_500)
        self.assertEqual(len(self.gamification.events), 1)

    def test_summary_repository_records_personal_best(self) -> None:
        summary = FakeSummaryRepository()
        custom_service = TimerLeaderboardService(
            self.redis,
            self.signer,
            gamification_service=self.gamification,
            rate_limiter=RedisRateLimiter(self.redis, max_attempts=3, window_seconds=60),
            summary_repository=summary,
        )
        api = TimerLeaderboardAPI(custom_service)

        payload = self._payload_for("achiever", time_ms=90_000)
        status, body = api.post_timer("achiever", payload)
        self.assertEqual(status, 200)
        self.assertTrue(body["personalBest"])
        self.assertEqual(len(summary.records), 1)
        self.assertEqual(summary.records[0]["rank"], 1)
        self.assertEqual(summary.records[0]["time_ms"], 90_000)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
