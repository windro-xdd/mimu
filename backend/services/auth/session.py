from __future__ import annotations

from datetime import timedelta
from typing import Dict, Optional, Tuple

from fastapi import Response

from .config import AuthSettings, settings
from .models import User
from .repository import InMemoryUserRepository
from .security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_csrf_token,
)


class RefreshTokenStore:
    """Keeps track of active refresh tokens for rotation and revocation."""

    def __init__(self) -> None:
        self._store: Dict[str, int] = {}

    def add(self, jti: str, user_id: int) -> None:
        self._store[jti] = user_id

    def revoke(self, jti: Optional[str]) -> None:
        if jti:
            self._store.pop(jti, None)

    def is_active(self, jti: str) -> bool:
        return jti in self._store

    def get_user_id(self, jti: str) -> Optional[int]:
        return self._store.get(jti)

    def reset(self) -> None:
        self._store.clear()


class AuthSessionManager:
    """Handles issuing, rotating, and revoking authentication cookies."""

    def __init__(
        self,
        repository: InMemoryUserRepository,
        *,
        config: AuthSettings = settings,
    ) -> None:
        self.repository = repository
        self.config = config
        self.refresh_tokens = RefreshTokenStore()

    def _cookie_common_kwargs(self) -> Dict[str, object]:
        kwargs: Dict[str, object] = {
            "secure": self.config.cookie_secure,
            "httponly": self.config.cookie_httponly,
            "samesite": self.config.cookie_samesite,
            "path": self.config.cookie_path,
        }
        if self.config.cookie_domain:
            kwargs["domain"] = self.config.cookie_domain
        return kwargs

    def _set_cookie(
        self,
        response: Response,
        *,
        key: str,
        value: str,
        max_age: int,
        httponly: Optional[bool] = None,
    ) -> None:
        kwargs = self._cookie_common_kwargs()
        if httponly is not None:
            kwargs["httponly"] = httponly
        response.set_cookie(key, value, max_age=max_age, **kwargs)

    def _session_cookie_durations(self) -> Tuple[int, int, int]:
        access_seconds = int(timedelta(minutes=self.config.access_token_expiration_minutes).total_seconds())
        refresh_seconds = int(
            timedelta(minutes=self.config.refresh_token_expiration_minutes).total_seconds()
        )
        csrf_seconds = int(
            timedelta(minutes=self.config.csrf_token_expiration_minutes).total_seconds()
        )
        return access_seconds, refresh_seconds, csrf_seconds

    def establish_session(self, response: Response, user: User, *, previous_jti: Optional[str] = None) -> Dict[str, str]:
        if previous_jti:
            self.refresh_tokens.revoke(previous_jti)

        access_token = create_access_token(user, config=self.config)
        refresh_token, jti = create_refresh_token(user, config=self.config)
        csrf_token = generate_csrf_token()

        self.refresh_tokens.add(jti, user.id)

        access_age, refresh_age, csrf_age = self._session_cookie_durations()
        self._set_cookie(response, key="access_token", value=access_token, max_age=access_age)
        self._set_cookie(response, key="refresh_token", value=refresh_token, max_age=refresh_age)
        self._set_cookie(
            response,
            key="csrf_token",
            value=csrf_token,
            max_age=csrf_age,
            httponly=False,
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "csrf_token": csrf_token,
            "refresh_jti": jti,
        }

    def rotate_refresh_token(self, response: Response, refresh_token: str) -> Tuple[User, Dict[str, str]]:
        payload = decode_refresh_token(refresh_token, config=self.config)
        jti = payload.get("jti")
        if not jti or not self.refresh_tokens.is_active(jti):
            raise InvalidTokenError("Refresh token is no longer valid.")

        user_id = self.refresh_tokens.get_user_id(jti)
        if user_id is None:
            raise InvalidTokenError("Refresh token has been revoked.")

        user = self.repository.get_by_id(int(user_id))
        if user is None:
            raise InvalidTokenError("Associated user no longer exists.")

        token_data = self.establish_session(response, user, previous_jti=jti)
        return user, token_data

    def revoke_refresh_token(self, refresh_token: str, *, verify_exp: bool = False) -> None:
        try:
            payload = decode_refresh_token(refresh_token, config=self.config, verify_exp=verify_exp)
        except InvalidTokenError:
            return
        self.refresh_tokens.revoke(payload.get("jti"))

    def clear_session(self, response: Response) -> None:
        base_kwargs = self._cookie_common_kwargs()
        response.delete_cookie("access_token", **base_kwargs)
        response.delete_cookie("refresh_token", **base_kwargs)

        csrf_kwargs = dict(base_kwargs)
        csrf_kwargs["httponly"] = False
        response.delete_cookie("csrf_token", **csrf_kwargs)

    def reset(self) -> None:
        self.refresh_tokens.reset()
