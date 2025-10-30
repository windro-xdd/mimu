"""Application blueprint registration."""

from __future__ import annotations

from flask import Flask

from . import (
    admin,
    auth,
    content,
    excuses,
    health,
    leaderboard,
    users,
    votes,
)

BLUEPRINTS = (
    admin.bp,
    auth.bp,
    content.bp,
    excuses.bp,
    health.bp,
    leaderboard.bp,
    users.bp,
    votes.bp,
)


def register_blueprints(app: Flask) -> None:
    """Attach all blueprints to the provided Flask application."""
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
