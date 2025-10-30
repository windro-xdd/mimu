"""Minimal WSGI application exposing leaderboard endpoints."""

from __future__ import annotations

import json
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs

from .models import LeaderboardEntry
from .service import LeaderboardService

Environ = Dict[str, object]
StartResponse = Callable[[str, List[Tuple[str, str]], Optional[BaseException]], None]

_STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    405: "Method Not Allowed",
}

_JSON_CONTENT_TYPE = "application/json; charset=utf-8"


class LeaderboardAPI:
    """WSGI-compatible callable for serving leaderboard endpoints."""

    def __init__(self, service: LeaderboardService) -> None:
        self._service = service

    # WSGI entrypoint -----------------------------------------------------------
    def __call__(self, environ: Environ, start_response: StartResponse):
        method = str(environ.get("REQUEST_METHOD", "")).upper()
        path = str(environ.get("PATH_INFO", ""))
        query_string = str(environ.get("QUERY_STRING", ""))

        if method != "GET":
            return self._method_not_allowed(start_response)

        if path == "/api/leaderboard/score":
            return self._handle_score(query_string, start_response)

        if path == "/api/leaderboard/timer":
            return self._handle_timer(query_string, start_response)

        return self._not_found(start_response)

    # Endpoint handlers ---------------------------------------------------------
    def _handle_score(self, query_string: str, start_response: StartResponse):
        try:
            limit = self._parse_limit(query_string)
        except ValueError as exc:
            return self._bad_request(str(exc), start_response)

        entries = self._service.get_score_leaderboard(limit=limit)
        return self._json_response(entries, start_response)

    def _handle_timer(self, query_string: str, start_response: StartResponse):
        try:
            limit = self._parse_limit(query_string)
        except ValueError as exc:
            return self._bad_request(str(exc), start_response)

        entries = self._service.get_timer_leaderboard(limit=limit)
        return self._json_response(entries, start_response)

    # Response helpers ----------------------------------------------------------
    def _json_response(
        self, entries: Iterable[LeaderboardEntry], start_response: StartResponse
    ):
        payload = {"entries": [entry.as_dict() for entry in entries]}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status = 200
        headers = [
            ("Content-Type", _JSON_CONTENT_TYPE),
            ("Content-Length", str(len(body))),
        ]
        start_response(self._format_status(status), headers, None)
        return [body]

    def _bad_request(self, message: str, start_response: StartResponse):
        payload = {"error": message}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status = 400
        headers = [
            ("Content-Type", _JSON_CONTENT_TYPE),
            ("Content-Length", str(len(body))),
        ]
        start_response(self._format_status(status), headers, None)
        return [body]

    def _not_found(self, start_response: StartResponse):
        payload = {"error": "Not Found"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status = 404
        headers = [
            ("Content-Type", _JSON_CONTENT_TYPE),
            ("Content-Length", str(len(body))),
        ]
        start_response(self._format_status(status), headers, None)
        return [body]

    def _method_not_allowed(self, start_response: StartResponse):
        payload = {"error": "Method Not Allowed"}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status = 405
        headers = [
            ("Content-Type", _JSON_CONTENT_TYPE),
            ("Content-Length", str(len(body))),
            ("Allow", "GET"),
        ]
        start_response(self._format_status(status), headers, None)
        return [body]

    # Utilities -----------------------------------------------------------------
    @staticmethod
    def _parse_limit(query_string: str) -> Optional[int]:
        if not query_string:
            return None

        params = parse_qs(query_string, keep_blank_values=True)
        values = params.get("limit")
        if not values:
            return None

        if values[0] in {"", None}:
            raise ValueError("limit must be an integer")

        try:
            limit = int(values[0])
        except (TypeError, ValueError) as exc:
            raise ValueError("limit must be an integer") from exc

        if limit < 0:
            return 0

        return limit

    @staticmethod
    def _format_status(status_code: int) -> str:
        reason = _STATUS_TEXT.get(status_code, "")
        return f"{status_code} {reason}".rstrip()


def create_leaderboard_api(
    redis_client,
    user_repository,
    *,
    score_key: str = None,
    timer_key: str = None,
    max_entries: int = None,
) -> LeaderboardAPI:
    """Factory helper to wire dependencies into the API."""

    service_kwargs: Dict[str, object] = {}
    if score_key:
        service_kwargs["score_key"] = score_key
    if timer_key:
        service_kwargs["timer_key"] = timer_key
    if max_entries:
        service_kwargs["max_entries"] = max_entries

    service = LeaderboardService(redis_client, user_repository, **service_kwargs)
    return LeaderboardAPI(service)
