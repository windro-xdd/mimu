"""Lightweight WSGI application exposing the excuse API."""

from __future__ import annotations

import json
from typing import Callable, Iterable, List, Optional, Tuple

from .excuses import ExcuseService, get_excuse_service

StartResponse = Callable[[str, List[Tuple[str, str]], Optional[Tuple]], None]
WSGIApplication = Callable[[dict, StartResponse], Iterable[bytes]]


class ExcuseAPI:
    """Minimal WSGI-compatible application exposing the excuse endpoint."""

    def __init__(self, service: ExcuseService):
        self._service = service

    @property
    def service(self) -> ExcuseService:
        return self._service

    def __call__(self, environ: dict, start_response: StartResponse) -> Iterable[bytes]:
        path = environ.get("PATH_INFO", "") or "/"
        path = path.rstrip("/") if path != "/" else path
        method = (environ.get("REQUEST_METHOD") or "GET").upper()

        if path == "/api/excuse":
            if method != "GET":
                return self._method_not_allowed(start_response)
            return self._excuse_response(start_response)

        return self._not_found(start_response)

    def _json_response(
        self,
        start_response: StartResponse,
        status: str,
        payload: dict,
        extra_headers: Optional[List[Tuple[str, str]]] = None,
    ) -> Iterable[bytes]:
        body = json.dumps(payload).encode("utf-8")
        headers: List[Tuple[str, str]] = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        if extra_headers:
            headers.extend(extra_headers)

        start_response(status, headers)
        return [body]

    def _excuse_response(self, start_response: StartResponse) -> Iterable[bytes]:
        return self._json_response(
            start_response,
            "200 OK",
            {"excuse": self._service.get_random_excuse()},
        )

    def _not_found(self, start_response: StartResponse) -> Iterable[bytes]:
        return self._json_response(start_response, "404 Not Found", {"detail": "Not Found"})

    def _method_not_allowed(self, start_response: StartResponse) -> Iterable[bytes]:
        return self._json_response(
            start_response,
            "405 Method Not Allowed",
            {"detail": "Method Not Allowed"},
            extra_headers=[("Allow", "GET")],
        )


def create_excuse_app(service: Optional[ExcuseService] = None) -> WSGIApplication:
    """Build the excuse API WSGI application."""

    return ExcuseAPI(service or get_excuse_service())


__all__ = ["ExcuseAPI", "create_excuse_app"]
