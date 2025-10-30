"""Excuse seeding and retrieval utilities."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

DEFAULT_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "excuses.json"


class ExcuseSeedError(RuntimeError):
    """Raised when excuse seed data cannot be loaded."""


def _coerce_excuse_list(values: Iterable[object]) -> Tuple[str, ...]:
    """Normalise raw seed data into a tuple of unique, non-empty excuses."""

    seen = set()
    processed = []

    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        processed.append(text)
        seen.add(text)

    if not processed:
        raise ExcuseSeedError("Excuse list must contain at least one non-empty string.")

    return tuple(processed)


def load_excuse_fixture(path: Path) -> Tuple[str, ...]:
    """Load excuse strings from a JSON fixture file."""

    if not path.exists():
        raise ExcuseSeedError(f"Excuse fixture not found at '{path}'.")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ExcuseSeedError(f"Unable to decode excuse fixture '{path}'.") from exc

    if isinstance(raw, dict):
        if "excuses" not in raw:
            raise ExcuseSeedError("Excuse fixture dictionary must include an 'excuses' key.")
        raw_values = raw["excuses"]
    else:
        raw_values = raw

    if not isinstance(raw_values, list):
        raise ExcuseSeedError("Excuse fixture must resolve to a list of strings.")

    return _coerce_excuse_list(raw_values)


@dataclass(frozen=True)
class ExcuseSeedConfig:
    """Configuration for loading excuse seed data."""

    fixture_path: Optional[Path] = None
    excuses: Optional[Sequence[str]] = None

    @classmethod
    def from_env(cls) -> "ExcuseSeedConfig":
        fixture = os.getenv("EXCUSE_FIXTURE_PATH")
        return cls(fixture_path=Path(fixture) if fixture else None)

    def resolve_excuses(self) -> Tuple[str, ...]:
        if self.excuses is not None:
            return _coerce_excuse_list(self.excuses)

        path = self.fixture_path or DEFAULT_FIXTURE_PATH
        return load_excuse_fixture(path)


class ExcuseService:
    """Service responsible for retrieving excuses."""

    def __init__(self, excuses: Sequence[str]):
        self._excuses = _coerce_excuse_list(excuses)

    @property
    def excuses(self) -> Tuple[str, ...]:
        return self._excuses

    def get_random_excuse(self) -> str:
        return random.choice(self._excuses)


def get_excuse_service(config: Optional[ExcuseSeedConfig] = None) -> ExcuseService:
    """Factory that builds an :class:`ExcuseService` from the provided configuration."""

    config = config or ExcuseSeedConfig()
    return ExcuseService(config.resolve_excuses())


__all__ = [
    "ExcuseSeedConfig",
    "ExcuseSeedError",
    "ExcuseService",
    "DEFAULT_FIXTURE_PATH",
    "get_excuse_service",
    "load_excuse_fixture",
]
