"""Dashboard routes (IMPL-0002 Milestone D4).

Read-only aggregation over the latest assessment, its posture checks, findings
priority counts, and (if any) completion row. All state is derived at read-time
per ADR-0025 section 2 — no ``is_complete`` flag.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from opensec.db.connection import get_db
from opensec.db.dao.assessment import get_latest_assessment
from opensec.db.dao.completion import get_completion_for_assessment
from opensec.db.dao.posture_check import count_posture_pass_total
from opensec.db.repo_finding import count_findings_by_priority
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
async def get_dashboard(db=Depends(get_db)) -> DashboardPayload:
    """Aggregate dashboard payload: latest assessment + findings + posture.

    The findings count is scoped to the current assessment window (source
    ``opensec-assessment``, created at or after the latest assessment's start)
    so the Vulnerabilities tile always matches what the Findings page shows.
    """
    latest = await get_latest_assessment(db)

    if latest is None:
        return DashboardPayload(
            assessment=None,
            grade=None,
            criteria=CriteriaSnapshot(),
            findings_count_by_priority={},
            posture_pass_count=0,
            posture_total_count=0,
            completion_id=None,
        )

    counts = await count_findings_by_priority(
        db,
        source_type="opensec-assessment",
        created_since_iso=latest.started_at,
    )
    pass_count, total_count = await count_posture_pass_total(db, latest.id)
    completion = await get_completion_for_assessment(db, latest.id)

    # A completion row can outlive the state that created it (new vuln lands
    # post-completion, a posture check regresses). Suppress the celebration
    # when the current snapshot no longer actually meets every criterion.
    snapshot = latest.criteria_snapshot or CriteriaSnapshot()
    completion_id = (
        completion.id
        if completion is not None
        and latest.grade == "A"
        and snapshot.all_met()
        else None
    )

    return DashboardPayload(
        assessment=latest,
        grade=latest.grade,
        criteria=snapshot,
        findings_count_by_priority=counts,
        posture_pass_count=pass_count,
        posture_total_count=total_count,
        completion_id=completion_id,
    )
