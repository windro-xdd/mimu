from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Protocol, Tuple


class RedisSortedSetClient(Protocol):
    """Protocol describing the redis primitives used by the leaderboard service."""

    def zscore(self, name: str, member: str) -> Optional[float]:
        ...

    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        ...

    def zrank(self, name: str, member: str) -> Optional[int]:
        ...

    def zcard(self, name: str) -> int:
        ...


class RedisRateLimitClient(Protocol):
    """Protocol describing redis primitives required for rate limiting."""

    def incr(self, key: str) -> int:
        ...

    def expire(self, key: str, ttl_seconds: int) -> None:
        ...

    def ttl(self, key: str) -> int:
        ...


class GamificationService(Protocol):
    """Minimal interface for triggering downstream gamification rules."""

    def trigger_top_timer(self, user_id: str, rank: int, time_ms: int) -> None:
        ...


class TimerSummaryRepository(Protocol):
    """Optional persistence layer for recording timer achievements."""

    def record_personal_best(
        self, user_id: str, time_ms: int, started_at_ms: int, rank: Optional[int]
    ) -> None:
        ...


@dataclass(frozen=True)
class TimerSubmissionPayload:
    """Incoming payload for timer submissions."""

    time_ms: int
    started_at_ms: int
    token: str

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TimerSubmissionPayload":
        try:
            time_ms = int(payload["time_ms"])
            started_at_ms = int(payload["started_at_ms"])
            token = str(payload["token"])
        except KeyError as exc:  # pragma: no cover - defensive
            raise TimerValidationError(f"Missing required field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise TimerValidationError("Invalid payload types") from exc
        return cls(time_ms=time_ms, started_at_ms=started_at_ms, token=token)


@dataclass(frozen=True)
class TimerSubmissionResult:
    """Result of a timer submission."""

    status: str
    personal_best: bool
    best_time_ms: int
    rank: Optional[int]
    top_ten: bool
    attempts_remaining: Optional[int] = None
    retry_after_seconds: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "personalBest": self.personal_best,
            "bestTimeMs": self.best_time_ms,
            "rank": self.rank,
            "topTen": self.top_ten,
            "attemptsRemaining": self.attempts_remaining,
            "retryAfterSeconds": self.retry_after_seconds,
        }


class TimerSubmissionError(RuntimeError):
    """Base exception for submission failures."""


class TimerValidationError(TimerSubmissionError):
    """Raised when a submission fails basic validation."""


class TimerTokenError(TimerSubmissionError):
    """Raised when anti-cheat token validation fails."""


class TimerRateLimitExceeded(TimerSubmissionError):
    """Raised when a user exceeds the submission rate limit."""

    def __init__(self, retry_after_seconds: int, attempts_remaining: int) -> None:
        super().__init__("Rate limit exceeded")
        self.retry_after_seconds = retry_after_seconds
        self.attempts_remaining = attempts_remaining


class TimerTokenSigner:
    """Signs and validates timer start tokens using HMAC."""

    def __init__(
        self,
        secret: str,
        *,
        max_start_age_ms: int = 10 * 60 * 1000,
        max_future_skew_ms: int = 5 * 1000,
        now_provider: Optional[Callable[[], int]] = None,
    ) -> None:
        if not secret:
            raise ValueError("secret must be provided")
        self._secret = secret.encode("utf-8")
        self._max_start_age_ms = max_start_age_ms
        self._max_future_skew_ms = max_future_skew_ms
        self._now_provider = now_provider or (lambda: int(time.time() * 1000))

    def issue_token(self, user_id: str, started_at_ms: int) -> str:
        message = self._build_message(user_id, started_at_ms)
        signature = hmac.new(self._secret, message, hashlib.sha256).hexdigest()
        return signature

    def validate_token(self, token: str, user_id: str, started_at_ms: int) -> None:
        expected = self.issue_token(user_id, started_at_ms)
        if not hmac.compare_digest(expected, token):
            raise TimerTokenError("Invalid timer token")

        now_ms = self._now_provider()
        if started_at_ms > now_ms + self._max_future_skew_ms:
            raise TimerTokenError("Start time appears to be from the future")
        if now_ms - started_at_ms > self._max_start_age_ms:
            raise TimerTokenError("Start token has expired")

    def _build_message(self, user_id: str, started_at_ms: int) -> bytes:
        return f"{user_id}:{started_at_ms}".encode("utf-8")


@dataclass(frozen=True)
class RateLimitInfo:
    allowed: bool
    attempts_remaining: int
    retry_after_seconds: int


class RedisRateLimiter:
    """Simple fixed-window rate limiter backed by Redis."""

    def __init__(
        self,
        redis: RedisRateLimitClient,
        *,
        key_prefix: str = "timer:rate",
        max_attempts: int = 5,
        window_seconds: int = 60,
    ) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self._redis = redis
        self._key_prefix = key_prefix
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    def hit(self, user_id: str) -> RateLimitInfo:
        key = f"{self._key_prefix}:{user_id}"
        count = int(self._redis.incr(key))
        if count == 1:
            self._redis.expire(key, self._window_seconds)
        ttl = self._redis.ttl(key)
        retry_after = ttl if ttl >= 0 else int(self._window_seconds)
        attempts_remaining = max(0, self._max_attempts - count)
        allowed = count <= self._max_attempts
        return RateLimitInfo(
            allowed=allowed,
            attempts_remaining=attempts_remaining,
            retry_after_seconds=retry_after,
        )


class TimerLeaderboardService:
    """Handles timer submissions and leaderboard updates."""

    def __init__(
        self,
        redis: RedisSortedSetClient,
        token_signer: TimerTokenSigner,
        gamification_service: Optional[GamificationService] = None,
        *,
        leaderboard_key: str = "leaderboard:timer",
        rate_limiter: Optional[RedisRateLimiter] = None,
        summary_repository: Optional[TimerSummaryRepository] = None,
        top_n: int = 10,
        max_time_ms: int = 24 * 60 * 60 * 1000,
    ) -> None:
        if top_n <= 0:
            raise ValueError("top_n must be positive")
        self._redis = redis
        self._token_signer = token_signer
        self._gamification = gamification_service
        self._leaderboard_key = leaderboard_key
        self._rate_limiter = rate_limiter
        self._summary_repo = summary_repository
        self._top_n = top_n
        self._max_time_ms = max_time_ms

    def submit_time(self, user_id: str, payload: TimerSubmissionPayload) -> TimerSubmissionResult:
        self._token_signer.validate_token(payload.token, user_id, payload.started_at_ms)

        rate_info: Optional[RateLimitInfo] = None
        if self._rate_limiter is not None:
            rate_info = self._rate_limiter.hit(user_id)
            if not rate_info.allowed:
                raise TimerRateLimitExceeded(
                    rate_info.retry_after_seconds, rate_info.attempts_remaining
                )

        if payload.time_ms <= 0:
            raise TimerValidationError("Completion time must be positive")
        if payload.time_ms > self._max_time_ms:
            raise TimerValidationError("Completion time exceeds allowable threshold")

        previous_best_score = self._redis.zscore(self._leaderboard_key, user_id)
        previous_rank_zero = self._redis.zrank(self._leaderboard_key, user_id)
        personal_best = (
            previous_best_score is None or payload.time_ms < previous_best_score
        )
        if personal_best:
            self._redis.zadd(self._leaderboard_key, {user_id: float(payload.time_ms)})
            if self._summary_repo is not None:
                self._summary_repo.record_personal_best(
                    user_id=user_id,
                    time_ms=payload.time_ms,
                    started_at_ms=payload.started_at_ms,
                    rank=self._rank_or_none(self._redis.zrank(self._leaderboard_key, user_id)),
                )
            best_time_ms = payload.time_ms
        elif previous_best_score is not None:
            best_time_ms = int(previous_best_score)
        else:
            best_time_ms = payload.time_ms

        current_rank = self._rank_or_none(
            self._redis.zrank(self._leaderboard_key, user_id)
        )
        top_ten = current_rank is not None and current_rank <= self._top_n
        entered_top_ten = False
        if personal_best and self._gamification is not None and current_rank is not None:
            previous_rank = self._rank_or_none(previous_rank_zero)
            if previous_rank is None or previous_rank > self._top_n:
                entered_top_ten = current_rank <= self._top_n
            if entered_top_ten:
                self._gamification.trigger_top_timer(
                    user_id=user_id, rank=current_rank, time_ms=best_time_ms
                )

        return TimerSubmissionResult(
            status="accepted",
            personal_best=personal_best,
            best_time_ms=best_time_ms,
            rank=current_rank,
            top_ten=top_ten,
            attempts_remaining=rate_info.attempts_remaining if rate_info else None,
            retry_after_seconds=rate_info.retry_after_seconds if rate_info else None,
        )

    def _rank_or_none(self, rank_zero_indexed: Optional[int]) -> Optional[int]:
        if rank_zero_indexed is None:
            return None
        return rank_zero_indexed + 1


class TimerLeaderboardAPI:
    """Lightweight façade mimicking an HTTP route handler."""

    def __init__(self, service: TimerLeaderboardService) -> None:
        self._service = service

    def post_timer(
        self, user_id: str, payload: Dict[str, Any]
    ) -> Tuple[int, Dict[str, Any]]:
        try:
            submission = TimerSubmissionPayload.from_dict(payload)
            result = self._service.submit_time(user_id, submission)
        except TimerRateLimitExceeded as exc:
            body = {
                "status": "rate_limited",
                "detail": "Too many submissions",
                "attemptsRemaining": exc.attempts_remaining,
                "retryAfterSeconds": exc.retry_after_seconds,
            }
            return 429, body
        except TimerTokenError as exc:
            body = {"status": "invalid_token", "detail": str(exc)}
            return 400, body
        except TimerValidationError as exc:
            body = {"status": "invalid_submission", "detail": str(exc)}
            return 422, body
        return 200, result.to_dict()


__all__ = [
    "GamificationService",
    "RateLimitInfo",
    "RedisRateLimiter",
    "RedisRateLimitClient",
    "RedisSortedSetClient",
    "TimerLeaderboardAPI",
    "TimerLeaderboardService",
    "TimerRateLimitExceeded",
    "TimerSubmissionError",
    "TimerSubmissionPayload",
    "TimerSubmissionResult",
    "TimerSummaryRepository",
    "TimerTokenError",
    "TimerTokenSigner",
    "TimerValidationError",
]
