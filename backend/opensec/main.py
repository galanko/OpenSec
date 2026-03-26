"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from opensec.api.routes import (
    agent_runs,
    chat,
    findings,
    health,
    messages,
    sessions,
    sidebar,
    workspaces,
)
from opensec.config import settings
from opensec.db.connection import close_db, init_db
from opensec.engine.client import opencode_client
from opensec.engine.process import opencode_process

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start OpenCode on startup, stop on shutdown."""
    logger.info("Starting OpenSec...")
    # Initialize persistence layer.
    db_path = settings.resolve_data_dir() / "opensec.db"
    await init_db(db_path)
    # Start AI engine (non-fatal if unavailable).
    try:
        await opencode_process.start()
    except Exception:
        logger.exception("Failed to start OpenCode — app will run but engine is unavailable")
    yield
    logger.info("Shutting down OpenSec...")
    await opencode_client.close()
    await opencode_process.stop()
    await close_db()


app = FastAPI(
    title="OpenSec",
    description="Self-hosted cybersecurity remediation copilot",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for dev (Vite on 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router)
app.include_router(sessions.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(findings.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(agent_runs.router, prefix="/api")
app.include_router(sidebar.router, prefix="/api")

# Serve built frontend in production (when OPENSEC_STATIC_DIR is set)
_static_dir = Path(settings.static_dir) if settings.static_dir else None
if _static_dir and _static_dir.is_dir():
    # Serve static assets (JS, CSS, images) under /assets
    _assets_dir = _static_dir / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="static-assets")

    # SPA fallback: serve index.html for all non-API, non-health routes
    _index_html = _static_dir / "index.html"

    @app.get("/{full_path:path}")
    async def _spa_fallback(full_path: str) -> FileResponse:
        """Serve the SPA index.html for client-side routing."""
        # Try to serve a static file first (favicon, etc.)
        candidate = _static_dir / full_path
        if full_path and candidate.is_file() and _static_dir in candidate.resolve().parents:
            return FileResponse(str(candidate))
        return FileResponse(str(_index_html))
