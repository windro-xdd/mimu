from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt

from .config import AuthSettings, settings
from .models import User


class InvalidTokenError(Exception):
    """Raised when a JWT token cannot be decoded or validated."""


def hash_password(password: str) -> str:
    if not isinstance(password, str):
        raise TypeError("Password must be a string.")
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _base_payload(user: User) -> Dict[str, Any]:
    return {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": datetime.now(timezone.utc),
    }


def create_access_token(
    user: User,
    *,
    config: AuthSettings = settings,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    payload = _base_payload(user)
    payload["type"] = "access"
    expires_in = expires_delta or timedelta(minutes=config.access_token_expiration_minutes)
    payload["exp"] = datetime.now(timezone.utc) + expires_in
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, config.secret_key, algorithm=config.algorithm)


def create_refresh_token(
    user: User,
    *,
    config: AuthSettings = settings,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    payload = _base_payload(user)
    payload["type"] = "refresh"
    payload["jti"] = jti or secrets.token_urlsafe(16)
    expires_in = expires_delta or timedelta(minutes=config.refresh_token_expiration_minutes)
    payload["exp"] = datetime.now(timezone.utc) + expires_in
    if additional_claims:
        payload.update(additional_claims)
    token = jwt.encode(payload, config.secret_key, algorithm=config.algorithm)
    return token, payload["jti"]


def decode_token(
    token: str,
    *,
    expected_type: str,
    config: AuthSettings = settings,
    verify_exp: bool = True,
) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=[config.algorithm],
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError as exc:  # pragma: no cover - fast failure path
        raise InvalidTokenError("Token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token is invalid.") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise InvalidTokenError("Unexpected token type.")
    return payload


def decode_access_token(token: str, *, config: AuthSettings = settings) -> Dict[str, Any]:
    return decode_token(token, expected_type="access", config=config)


def decode_refresh_token(
    token: str,
    *,
    config: AuthSettings = settings,
    verify_exp: bool = True,
) -> Dict[str, Any]:
    return decode_token(token, expected_type="refresh", config=config, verify_exp=verify_exp)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
