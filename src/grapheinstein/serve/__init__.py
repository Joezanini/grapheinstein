"""Optional local HTTP serve surface (requires grapheinstein[serve])."""

from __future__ import annotations

from typing import Any

__all__ = [
    "ServeExtrasError",
    "ensure_serve_deps",
    "create_app",
    "run_server",
]


class ServeExtrasError(Exception):
    """Raised when optional [serve] Python packages are required but missing."""


def ensure_serve_deps() -> None:
    """Fail closed if serve is requested but FastAPI/Uvicorn are missing."""
    import importlib.util

    missing: list[str] = []
    if importlib.util.find_spec("fastapi") is None:
        missing.append("fastapi")
    if importlib.util.find_spec("uvicorn") is None:
        missing.append("uvicorn")
    if missing:
        raise ServeExtrasError(
            "Local HTTP serve requires optional extras "
            f"(missing: {', '.join(missing)}). "
            "Install with: pip install 'grapheinstein[serve]'"
        )


def create_app() -> Any:
    """Build the FastAPI application (lazy-imports FastAPI)."""
    ensure_serve_deps()
    from grapheinstein.serve.app import build_app

    return build_app()


def run_server(*, host: str = "127.0.0.1", port: int = 8000) -> None:
    """Start Uvicorn for the local serve app (blocks until shutdown)."""
    ensure_serve_deps()
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=host, port=port)
