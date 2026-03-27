"""Health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from opensec.config import settings
from opensec.engine.client import opencode_client
from opensec.engine.models import HealthStatus
from opensec.engine.process import opencode_process

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health() -> HealthStatus:
    oc_healthy = await opencode_process.health_check()

    # Read model from OpenCode runtime (not the file, which can be stale).
    model = ""
    if oc_healthy:
        try:
            config = await opencode_client.get_config()
            model = config.get("model", "")
        except Exception:
            pass
    if not model:
        model = settings.opencode_model

    return HealthStatus(
        opensec="ok",
        opencode="ok" if oc_healthy else "unavailable",
        opencode_version=settings.opencode_version,
        model=model,
    )
