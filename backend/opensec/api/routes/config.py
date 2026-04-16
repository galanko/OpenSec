"""Read-only config endpoints.

Exposes the feature-flag state plus a small bootstrap signal (has the user
completed onboarding, has any assessment ever been run) so the SPA's
first-run redirect + already-onboarded short-circuit can decide where to
send the user. This is the ONLY place where feature flags cross the
backend/frontend boundary — don't sprinkle flag checks across individual
routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from opensec.config import settings
from opensec.db.connection import get_db
from opensec.db.dao.assessment import get_latest_assessment
from opensec.db.repo_setting import get_setting

router = APIRouter(prefix="/config", tags=["config"])


class FeatureFlags(BaseModel):
    """Snapshot of server-side feature flags visible to the UI."""

    v1_1_from_zero_to_secure_enabled: bool
    onboarding_completed: bool
    has_any_assessment: bool


@router.get("/feature-flags", response_model=FeatureFlags)
async def get_feature_flags(db=Depends(get_db)) -> FeatureFlags:
    """Return feature flags + bootstrap hints for SPA redirect decisions."""
    setting = await get_setting(db, "onboarding.completed")
    onboarding_completed = False
    if setting is not None and isinstance(setting.value, dict):
        onboarding_completed = bool(setting.value.get("completed"))

    latest = await get_latest_assessment(db)

    return FeatureFlags(
        v1_1_from_zero_to_secure_enabled=settings.v1_1_from_zero_to_secure_enabled,
        onboarding_completed=onboarding_completed,
        has_any_assessment=latest is not None,
    )
