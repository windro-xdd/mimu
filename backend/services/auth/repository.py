from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Optional

from .models import User


class UserAlreadyExistsError(Exception):
    """Raised when attempting to create a user with a duplicate username or email."""


class UserNotFoundError(Exception):
    """Raised when a requested user record cannot be located."""


@dataclass
class NormalisedIdentifiers:
    username: str
    email: str


class InMemoryUserRepository:
    """Thread-safe in-memory repository for user records.

    This lightweight repository is well-suited for tests and local development.
    Future work can replace it with a database-backed implementation that reuses
    the same interface.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users_by_id: Dict[int, User] = {}
        self._users_by_username: Dict[str, int] = {}
        self._users_by_email: Dict[str, int] = {}
        self._next_id: int = 1

    @staticmethod
    def _normalise(username: str, email: str) -> NormalisedIdentifiers:
        return NormalisedIdentifiers(username=username.lower(), email=email.lower())

    def reset(self) -> None:
        with self._lock:
            self._users_by_id.clear()
            self._users_by_username.clear()
            self._users_by_email.clear()
            self._next_id = 1

    def create_user(self, username: str, email: str, password_hash: str, *, role: str = "user") -> User:
        normalised = self._normalise(username, email)
        with self._lock:
            if normalised.username in self._users_by_username:
                raise UserAlreadyExistsError("Username is already in use.")
            if normalised.email in self._users_by_email:
                raise UserAlreadyExistsError("Email address is already registered.")

            user = User(
                id=self._next_id,
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
            )
            self._users_by_id[self._next_id] = user
            self._users_by_username[normalised.username] = self._next_id
            self._users_by_email[normalised.email] = self._next_id
            self._next_id += 1
            return user

    def get_by_username(self, username: str) -> Optional[User]:
        normalised = username.lower()
        with self._lock:
            user_id = self._users_by_username.get(normalised)
            return self._users_by_id.get(user_id) if user_id is not None else None

    def get_by_email(self, email: str) -> Optional[User]:
        normalised = email.lower()
        with self._lock:
            user_id = self._users_by_email.get(normalised)
            return self._users_by_id.get(user_id) if user_id is not None else None

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._lock:
            return self._users_by_id.get(user_id)

    def update_role(self, user_id: int, role: str) -> User:
        with self._lock:
            user = self._users_by_id.get(user_id)
            if user is None:
                raise UserNotFoundError(f"User id {user_id} not found")
            user.role = role
            return user
