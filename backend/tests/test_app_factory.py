"""Tests for the Flask application factory setup."""

from __future__ import annotations

import os
from unittest import mock

from backend.app import create_app


def test_blueprints_registered():
    app = create_app("development")

    registered = set(app.blueprints.keys())
    expected = {
        "admin",
        "auth",
        "content",
        "excuses",
        "health",
        "leaderboard",
        "users",
        "votes",
    }

    assert expected.issubset(registered)


def test_healthcheck_endpoint_returns_payload():
    app = create_app("development")
    client = app.test_client()

    response = client.get("/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["status"] == app.config["HEALTHCHECK_MESSAGE"]
    if app.config.get("HEALTHCHECK_INCLUDE_ENVIRONMENT", True):
        assert payload["environment"] == app.config.get("ENVIRONMENT")


def test_environment_driven_configuration():
    with mock.patch.dict(
        os.environ,
        {
            "APP_CONFIG": "production",
            "HEALTHCHECK_MESSAGE": "ready",
            "FRONTEND_ORIGIN": "https://frontend.example",
        },
        clear=False,
    ):
        app = create_app()

    assert app.config["ENVIRONMENT"] == "production"
    assert app.config["HEALTHCHECK_MESSAGE"] == "ready"
    assert app.config["FRONTEND_ORIGIN"] == "https://frontend.example"
    assert app.config["DEBUG"] is False
