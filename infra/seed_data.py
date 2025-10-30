#!/usr/bin/env python3
"""Seed baseline data for the application database.

This script provisions default achievements, sample excuses, and an initial
administrative user. It is safe to run multiple times thanks to its
idempotent insert and update logic.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "backend" / "app.db"


@dataclass(frozen=True)
class AchievementSeed:
    code: str
    name: str
    description: str


@dataclass(frozen=True)
class ExcuseSeed:
    slug: str
    summary: str
    details: str
    category: str


DEFAULT_ACHIEVEMENTS: Tuple[AchievementSeed, ...] = (
    AchievementSeed(
        code="first_excuse",
        name="First Excuse Logged",
        description="Submit your first excuse through the platform.",
    ),
    AchievementSeed(
        code="streak_7",
        name="Seven Day Streak",
        description="Log excuses for seven consecutive days without missing a day.",
    ),
    AchievementSeed(
        code="creative_genius",
        name="Creative Genius",
        description="Submit an excuse that receives a top creativity rating from reviewers.",
    ),
)

SAMPLE_EXCUSES: Tuple[ExcuseSeed, ...] = (
    ExcuseSeed(
        slug="network-outage",
        summary="Blamed an unexpected network outage.",
        details="Claimed that the office squirrels chewed through the fibre line out front.",
        category="technical",
    ),
    ExcuseSeed(
        slug="transport-delays",
        summary="Cited catastrophic public transport delays.",
        details="Explained that three separate subway lines stalled due to simultaneous signal failures.",
        category="commute",
    ),
    ExcuseSeed(
        slug="timezone-mixup",
        summary="Missed a meeting due to a timezone mix-up.",
        details="Scheduled the client call using the wrong daylight saving rules for the region.",
        category="scheduling",
    ),
    ExcuseSeed(
        slug="hero-cat",
        summary="Rescued the office cat from a high shelf.",
        details="Had to climb onto stacked chairs to retrieve the cat before the fire alarm triggered.",
        category="misc",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed baseline application data.")
    parser.add_argument(
        "--database",
        "-d",
        default=os.getenv("SEED_DATABASE")
        or os.getenv("DATABASE_URL")
        or os.getenv("APP_DATABASE_URL")
        or f"sqlite:///{DEFAULT_DATABASE_PATH}",
        help="Database path or SQLite DSN (default: %(default)s)",
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("SEED_ADMIN_EMAIL", "admin@example.com"),
        help="Email for the seeded administrator account.",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!"),
        help="Password for the seeded administrator account.",
    )
    parser.add_argument(
        "--admin-name",
        default=os.getenv("SEED_ADMIN_NAME", "Initial Admin"),
        help="Display name for the seeded administrator account.",
    )
    parser.add_argument(
        "--skip-achievements",
        action="store_true",
        help="Skip inserting default achievements.",
    )
    parser.add_argument(
        "--skip-excuses",
        action="store_true",
        help="Skip inserting sample excuses.",
    )
    return parser.parse_args()


def resolve_database_path(database: str) -> Path:
    """Resolve a database DSN or file path to a concrete filesystem path."""

    if database.startswith("sqlite:///"):
        database_path = Path(database.replace("sqlite:///", "", 1))
    elif database.startswith("sqlite://"):
        raise ValueError(
            f"Only sqlite:/// style URLs are supported. Received: {database}."
        )
    elif "://" in database:
        raise ValueError(
            f"Unsupported database URL scheme. Only sqlite:/// is supported (received: {database})."
        )
    else:
        database_path = Path(database)

    if not database_path.is_absolute():
        database_path = (PROJECT_ROOT / database_path).resolve()

    database_path.parent.mkdir(parents=True, exist_ok=True)
    return database_path


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create required tables if they do not already exist."""

    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS excuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL,
            details TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            full_name TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def seed_achievements(
    connection: sqlite3.Connection, achievements: Iterable[AchievementSeed]
) -> Tuple[int, int]:
    """Insert or update default achievements.

    Returns a tuple containing counts for inserted and updated records.
    """

    inserted = 0
    updated = 0

    for achievement in achievements:
        existing = connection.execute(
            "SELECT name, description FROM achievements WHERE code = ?",
            (achievement.code,),
        ).fetchone()

        if existing is None:
            connection.execute(
                "INSERT INTO achievements (code, name, description) VALUES (?, ?, ?)",
                (achievement.code, achievement.name, achievement.description),
            )
            inserted += 1
            continue

        if (
            existing["name"] != achievement.name
            or existing["description"] != achievement.description
        ):
            connection.execute(
                "UPDATE achievements SET name = ?, description = ? WHERE code = ?",
                (achievement.name, achievement.description, achievement.code),
            )
            updated += 1

    return inserted, updated


def seed_excuses(
    connection: sqlite3.Connection, excuses: Iterable[ExcuseSeed]
) -> Tuple[int, int]:
    """Insert or update sample excuses.

    Returns a tuple containing counts for inserted and updated records.
    """

    inserted = 0
    updated = 0

    for excuse in excuses:
        existing = connection.execute(
            "SELECT summary, details, category FROM excuses WHERE slug = ?",
            (excuse.slug,),
        ).fetchone()

        if existing is None:
            connection.execute(
                "INSERT INTO excuses (slug, summary, details, category) VALUES (?, ?, ?, ?)",
                (excuse.slug, excuse.summary, excuse.details, excuse.category),
            )
            inserted += 1
            continue

        if (
            existing["summary"] != excuse.summary
            or existing["details"] != excuse.details
            or existing["category"] != excuse.category
        ):
            connection.execute(
                "UPDATE excuses SET summary = ?, details = ?, category = ? WHERE slug = ?",
                (excuse.summary, excuse.details, excuse.category, excuse.slug),
            )
            updated += 1

    return inserted, updated


def derive_password_hash(password: str, salt_hex: str) -> str:
    """Derive a PBKDF2-HMAC password hash using the provided salt."""

    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 390000)
    return derived.hex()


def ensure_admin_user(
    connection: sqlite3.Connection,
    *,
    email: str,
    password: str,
    full_name: str,
) -> Tuple[bool, bool]:
    """Ensure that an administrator user exists.

    Returns a tuple indicating whether the user was inserted or updated.
    """

    existing = connection.execute(
        "SELECT id, password_salt, password_hash, is_admin, full_name FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if existing is None:
        salt = secrets.token_hex(16)
        password_hash = derive_password_hash(password, salt)
        connection.execute(
            """
            INSERT INTO users (email, password_hash, password_salt, full_name, is_admin)
            VALUES (?, ?, ?, ?, 1)
            """,
            (email, password_hash, salt, full_name),
        )
        return True, False

    salt = existing["password_salt"] or secrets.token_hex(16)
    password_hash = derive_password_hash(password, salt)

    needs_update = (
        existing["password_hash"] != password_hash
        or existing["is_admin"] != 1
        or (full_name and existing["full_name"] != full_name)
    )

    if needs_update:
        connection.execute(
            "UPDATE users SET password_hash = ?, password_salt = ?, full_name = ?, is_admin = 1 WHERE email = ?",
            (password_hash, salt, full_name, email),
        )
        return False, True

    return False, False


def main() -> None:
    args = parse_args()
    database_path = resolve_database_path(args.database)

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        initialize_schema(connection)

        achievements_result = (0, 0)
        if not args.skip_achievements:
            achievements_result = seed_achievements(connection, DEFAULT_ACHIEVEMENTS)

        excuses_result = (0, 0)
        if not args.skip_excuses:
            excuses_result = seed_excuses(connection, SAMPLE_EXCUSES)

        inserted_admin, updated_admin = ensure_admin_user(
            connection,
            email=args.admin_email,
            password=args.admin_password,
            full_name=args.admin_name,
        )

        connection.commit()

    achievements_inserted, achievements_updated = achievements_result
    excuses_inserted, excuses_updated = excuses_result

    print("Seed data complete:")
    if not args.skip_achievements:
        print(
            f"  Achievements - inserted: {achievements_inserted}, updated: {achievements_updated}"
        )
    else:
        print("  Achievements - skipped")

    if not args.skip_excuses:
        print(f"  Excuses - inserted: {excuses_inserted}, updated: {excuses_updated}")
    else:
        print("  Excuses - skipped")

    print(
        "  Admin user - "
        + ("inserted" if inserted_admin else "updated" if updated_admin else "unchanged")
    )
    print(f"  Database path: {database_path}")


if __name__ == "__main__":
    main()
