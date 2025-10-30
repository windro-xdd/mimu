"""Flask extensions and database initialization for backend."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

# Centralized SQLAlchemy instance to avoid import cycles
db = SQLAlchemy()

__all__ = ["db"]