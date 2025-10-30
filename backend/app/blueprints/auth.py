"""Auth blueprint for authentication routes."""

from __future__ import annotations

from flask import Blueprint

from backend.services.auth import app as auth_app

bp = auth_app

__all__ = ["bp"]
