"""web.server module."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from voice_triage.http.rest import (
    TriageApi,
    _discover_piper_voices,
    create_api_router,
    initialize_runtime,
)


def create_app() -> FastAPI:
    """Create app."""
    runtime = initialize_runtime()
    api = TriageApi(runtime=runtime, public_api_prefix="/api/v1")
    static_dir = Path(__file__).resolve().parent / "static"

    app = FastAPI(title="Voice Triage Local UI", version="0.1.0")
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        """Health."""
        return {"status": "ok"}

    @app.get("/")
    def index() -> FileResponse:
        """Index."""
        return FileResponse(static_dir / "index.html")

    # Primary REST API surface for external clients and local web app.
    app.include_router(create_api_router(api, prefix="/api/v1", include_in_schema=True))
    # Backward-compatible aliases for existing clients/scripts.
    app.include_router(create_api_router(api, prefix="/api", include_in_schema=False))
    return app


__all__ = ["_discover_piper_voices", "create_app"]
