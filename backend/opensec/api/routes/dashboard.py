"""Dashboard routes (IMPL-0002 Milestone D4).

Session-0 contract stub. Real implementation ships in Session B.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from opensec.models import Assessment, CriteriaSnapshot, Grade

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardPayload(BaseModel):
    assessment: Assessment | None
    grade: Grade | None
    criteria: CriteriaSnapshot
    findings_count_by_priority: dict[str, int]
    posture_pass_count: int
    posture_total_count: int
    completion_id: str | None = None


@router.get("", response_model=DashboardPayload)
async def get_dashboard() -> DashboardPayload:
    """Aggregate dashboard payload: latest assessment + findings + posture."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")
