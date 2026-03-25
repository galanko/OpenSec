"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from opensec.api.routes import chat, health, sessions
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
    try:
        await opencode_process.start()
    except Exception:
        logger.exception("Failed to start OpenCode — app will run but engine is unavailable")
    yield
    logger.info("Shutting down OpenSec...")
    await opencode_client.close()
    await opencode_process.stop()


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
