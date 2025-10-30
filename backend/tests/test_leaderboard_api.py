import io
import json
import unittest
from typing import Dict, Iterable, List, Tuple

from backend.services.leaderboard import (
    LeaderboardAPI,
    LeaderboardService,
    UserProfile,
)
from backend.services.leaderboard.service import DEFAULT_SCORE_KEY, DEFAULT_TIMER_KEY


class FakeRedisClient:
    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], List[Tuple[str, float]]] = {}

    def seed(self, method: str, key: str, values: List[Tuple[str, float]]) -> None:
        self._store[(method, key)] = values

    def zrevrange(self, key: str, start: int, end: int, *, withscores: bool = False):
        assert withscores, "Leaderboard service must request scores"
        data = self._store.get(("zrevrange", key), [])
        return self._slice(data, start, end)

    def zrange(self, key: str, start: int, end: int, *, withscores: bool = False):
        assert withscores, "Leaderboard service must request scores"
        data = self._store.get(("zrange", key), [])
        return self._slice(data, start, end)

    @staticmethod
    def _slice(data: List[Tuple[str, float]], start: int, end: int):
        length = len(data)
        if length == 0:
            return []

        start = max(start, 0)
        end = length - 1 if end < 0 else min(end, length - 1)
        if end < start:
            return []
        return data[start : end + 1]


class FakeUserRepository:
    def __init__(self, profiles: Iterable[UserProfile]) -> None:
        self._profiles = {profile.user_id: profile for profile in profiles}
        self.requested_ids: List[str] = []

    def get_profiles(self, user_ids: Iterable[str]):
        ids = list(user_ids)
        self.requested_ids = ids
        return {user_id: self._profiles[user_id] for user_id in ids if user_id in self._profiles}


class LeaderboardAPITestCase(unittest.TestCase):
    def make_environ(self, path: str, query_string: str = ""):
        return {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": path,
            "QUERY_STRING": query_string,
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(),
            "wsgi.errors": io.StringIO(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "SERVER_NAME": "testserver",
            "SERVER_PORT": "80",
            "SCRIPT_NAME": "",
        }

    def invoke(self, app: LeaderboardAPI, path: str, query_string: str = ""):
        environ = self.make_environ(path, query_string)
        status_container = {}
        headers_container = {}

        def start_response(status, headers, exc_info=None):  # noqa: ANN001
            status_container["status"] = status
            headers_container["headers"] = headers

        body_chunks = app(environ, start_response)
        body = b"".join(body_chunks).decode("utf-8")
        payload = json.loads(body)
        return status_container["status"], headers_container["headers"], payload

    def test_score_leaderboard_returns_hydrated_entries(self):
        redis_client = FakeRedisClient()
        redis_client.seed(
            "zrevrange",
            DEFAULT_SCORE_KEY,
            [
                ("42", 1520),
                ("7", 1490),
                ("3", 1275.5),
            ],
        )
        user_repo = FakeUserRepository(
            [
                UserProfile(user_id="42", username="Alice", avatar_url="https://cdn/a.png"),
                UserProfile(user_id="7", username="Bob"),
            ]
        )
        service = LeaderboardService(redis_client, user_repo)
        api = LeaderboardAPI(service)

        status, headers, payload = self.invoke(api, "/api/leaderboard/score")

        self.assertEqual(status, "200 OK")
        header_map = dict(headers)
        self.assertEqual(header_map["Content-Type"], "application/json; charset=utf-8")

        entries = payload["entries"]
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[0]["user_id"], "42")
        self.assertEqual(entries[0]["score"], 1520)
        self.assertEqual(entries[0]["username"], "Alice")
        self.assertEqual(entries[0]["avatar_url"], "https://cdn/a.png")
        self.assertEqual(entries[1]["rank"], 2)
        self.assertEqual(entries[1]["user_id"], "7")
        self.assertEqual(entries[1]["score"], 1490)
        self.assertEqual(entries[1]["username"], "Bob")
        self.assertIsNone(entries[1]["avatar_url"])
        self.assertEqual(entries[2]["rank"], 3)
        self.assertEqual(entries[2]["user_id"], "3")
        self.assertEqual(entries[2]["score"], 1275.5)
        self.assertIsNone(entries[2]["username"])
        self.assertIsNone(entries[2]["avatar_url"])
        self.assertEqual(user_repo.requested_ids, ["42", "7", "3"])

    def test_timer_leaderboard_returns_fastest_times_first(self):
        redis_client = FakeRedisClient()
        redis_client.seed(
            "zrange",
            DEFAULT_TIMER_KEY,
            [
                ("u1", 31.5),
                ("u2", 33.75),
                ("u3", 45.0),
            ],
        )
        user_repo = FakeUserRepository(
            [
                UserProfile(user_id="u2", username="Speedy"),
            ]
        )
        service = LeaderboardService(redis_client, user_repo)
        api = LeaderboardAPI(service)

        status, _, payload = self.invoke(api, "/api/leaderboard/timer")

        self.assertEqual(status, "200 OK")
        entries = payload["entries"]
        self.assertEqual([entry["user_id"] for entry in entries], ["u1", "u2", "u3"])
        self.assertEqual(entries[0]["time"], 31.5)
        self.assertEqual(entries[1]["time"], 33.75)
        self.assertEqual(entries[2]["time"], 45.0)
        self.assertEqual(entries[1]["username"], "Speedy")

    def test_limit_query_parameter_caps_results(self):
        redis_client = FakeRedisClient()
        sample = [(str(idx), float(1000 - idx)) for idx in range(150)]
        redis_client.seed("zrevrange", DEFAULT_SCORE_KEY, sample)
        user_repo = FakeUserRepository([])
        service = LeaderboardService(redis_client, user_repo)
        api = LeaderboardAPI(service)

        status, _, payload = self.invoke(api, "/api/leaderboard/score", "limit=150")

        self.assertEqual(status, "200 OK")
        entries = payload["entries"]
        self.assertEqual(len(entries), 100)
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[-1]["rank"], 100)

    def test_invalid_limit_returns_bad_request(self):
        redis_client = FakeRedisClient()
        user_repo = FakeUserRepository([])
        service = LeaderboardService(redis_client, user_repo)
        api = LeaderboardAPI(service)

        status, _, payload = self.invoke(api, "/api/leaderboard/score", "limit=abc")

        self.assertEqual(status, "400 Bad Request")
        self.assertEqual(payload["error"], "limit must be an integer")

    def test_unknown_path_returns_not_found(self):
        redis_client = FakeRedisClient()
        user_repo = FakeUserRepository([])
        service = LeaderboardService(redis_client, user_repo)
        api = LeaderboardAPI(service)

        status, _, payload = self.invoke(api, "/api/leaderboard/unknown")

        self.assertEqual(status, "404 Not Found")
        self.assertEqual(payload["error"], "Not Found")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
