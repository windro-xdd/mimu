from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AuthSettings:
    """Runtime configuration for the authentication service."""

    secret_key: str = os.getenv("AUTH_SECRET_KEY", "change-me-please")
    algorithm: str = os.getenv("AUTH_JWT_ALGORITHM", "HS256")
    access_token_expiration_minutes: int = int(
        os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15")
    )
    refresh_token_expiration_minutes: int = int(
        os.getenv("AUTH_REFRESH_TOKEN_MINUTES", str(60 * 24 * 7))
    )
    csrf_token_expiration_minutes: int = int(
        os.getenv("AUTH_CSRF_TOKEN_MINUTES", str(60 * 2))
    )
    cookie_domain: Optional[str] = os.getenv("AUTH_COOKIE_DOMAIN")
    cookie_path: str = os.getenv("AUTH_COOKIE_PATH", "/")
    cookie_secure: bool = _to_bool(os.getenv("AUTH_COOKIE_SECURE"), True)
    cookie_httponly: bool = True
    cookie_samesite: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()

    def __post_init__(self) -> None:
        if not self.secret_key or self.secret_key == "change-me-please":
            # In production this should be overridden; keeping the key predictable would be insecure.
            # We still allow the default during development and testing for convenience.
            self.secret_key = "change-me-please"

        allowed_samesite = {"lax", "strict", "none"}
        if self.cookie_samesite not in allowed_samesite:
            self.cookie_samesite = "lax"


settings = AuthSettings()
