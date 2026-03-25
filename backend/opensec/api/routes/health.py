"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from opensec.config import settings
from opensec.engine.models import HealthStatus
from opensec.engine.process import opencode_process

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    oc_healthy = await opencode_process.health_check()
    return HealthStatus(
        opensec="ok",
        opencode="ok" if oc_healthy else "unavailable",
        opencode_version=settings.opencode_version,
        model=settings.opencode_model,
    )
