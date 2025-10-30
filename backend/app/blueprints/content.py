"""Content blueprint for content-related routes."""

from __future__ import annotations

from flask import Blueprint

from backend.routes.content import content_bp

bp = content_bp

__all__ = ["bp"]
