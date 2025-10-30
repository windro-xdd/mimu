"""CLI entrypoint for running the backend Flask application."""

from __future__ import annotations

from backend.app import create_app
from backend.app.config import load_environment


def main() -> None:
    """Run the Flask development server."""
    load_environment()
    app = create_app()
    app.run(
        host=app.config.get("SERVER_HOST", "127.0.0.1"),
        port=int(app.config.get("SERVER_PORT", 5000)),
        debug=bool(app.config.get("DEBUG", False)),
    )


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    main()
