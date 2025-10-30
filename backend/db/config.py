"""Database configuration utilities."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

DEFAULT_DATABASE_URL = "sqlite:///app.db"


@dataclass(frozen=True)
class DatabaseConfig:
    """Lightweight container for database configuration."""

    url: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DatabaseConfig":
        """Build a configuration object from environment variables."""

        source: MutableMapping[str, str] = dict(os.environ if env is None else env)
        url = (
            source.get("DATABASE_URL")
            or source.get("SQLALCHEMY_DATABASE_URI")
            or DEFAULT_DATABASE_URL
        )
        return cls(url=url)


def get_engine(config: DatabaseConfig | None = None, **kwargs: Any) -> Engine:
    """Create a SQLAlchemy engine from the given configuration."""

    db_config = config or DatabaseConfig.from_env()
    return create_engine(db_config.url, **kwargs)


def get_sessionmaker(
    config: DatabaseConfig | None = None, **kwargs: Any
) -> sessionmaker:
    """Return a configured session factory bound to the engine."""

    engine = get_engine(config)
    return sessionmaker(bind=engine, **kwargs)


__all__ = ["DatabaseConfig", "get_engine", "get_sessionmaker", "DEFAULT_DATABASE_URL"]
