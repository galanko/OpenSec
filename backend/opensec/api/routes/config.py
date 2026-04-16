"""Read-only config endpoints.

Exposes the feature-flag state to the frontend so route guards can decide
whether to surface in-progress features. This is the ONLY place where
feature flags cross the backend/frontend boundary — don't sprinkle flag
checks across individual routes.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from opensec.config import settings

router = APIRouter(prefix="/config", tags=["config"])


class FeatureFlags(BaseModel):
    """Snapshot of server-side feature flags visible to the UI."""

    v1_1_from_zero_to_secure_enabled: bool


@router.get("/feature-flags", response_model=FeatureFlags)
async def get_feature_flags() -> FeatureFlags:
    """Return the current feature-flag values. Static; no auth gating required."""
    return FeatureFlags(
        v1_1_from_zero_to_secure_enabled=settings.v1_1_from_zero_to_secure_enabled,
    )
