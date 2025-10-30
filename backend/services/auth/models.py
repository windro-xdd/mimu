from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


@dataclass
class User:
    """Internal representation of a user account."""

    id: int
    username: str
    email: str
    password_hash: str
    role: str = "user"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="before")
    def strip_strings(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for key in ("username", "email", "password"):
                if isinstance(values.get(key), str):
                    values[key] = values[key].strip()
        return values


class LoginRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="before")
    def strip_data(cls, values: Any) -> Any:
        if isinstance(values, dict):
            for key in ("identifier", "password"):
                if isinstance(values.get(key), str):
                    values[key] = values[key].strip()
        return values


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_user(cls, user: User) -> "UserResponse":
        return cls(**user.to_public_dict())
