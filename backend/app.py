from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Tuple


class SimpleRequestHandler(BaseHTTPRequestHandler):
    """Lightweight HTTP handler used for local development and health checks."""

    server_version = "BackendPlaceholder/0.1"

    def _cors_headers(self) -> Tuple[str, str]:
        allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
        allowed_methods = os.getenv(
            "CORS_ALLOWED_METHODS",
            "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        )
        return allowed_origins, allowed_methods

    def _write_json(self, status_code: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        origin, methods = self._cors_headers()
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", methods)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Credentials", os.getenv("CORS_ALLOW_CREDENTIALS", "true"))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802 (http method name)
        origin, methods = self._cors_headers()
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", methods)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Credentials", os.getenv("CORS_ALLOW_CREDENTIALS", "true"))
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 (http method name)
        if self.path in {"/", "/health", "/healthz"}:
            payload = {
                "status": "ok",
                "service": "backend",
                "environment": os.getenv("APP_ENV", "development"),
            }
            self._write_json(200, payload)
            return

        self._write_json(404, {"detail": "Not found"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        """Silence default logging unless explicitly enabled."""

        if os.getenv("BACKEND_LOG_LEVEL", "info").lower() == "debug":
            super().log_message(format, *args)


def run() -> None:
    """Entrypoint used by the Docker container for local orchestration."""

    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    address = ("0.0.0.0", port)
    httpd = HTTPServer(address, SimpleRequestHandler)
    print(f"Backend development server listening on http://{address[0]}:{port}", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down backend server", flush=True)
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
