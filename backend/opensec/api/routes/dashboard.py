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
from opensec.db.dao.posture_check import list_posture_checks_for_assessment
from opensec.db.repo_finding import list_findings
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
    """Aggregate dashboard payload: latest assessment + findings + posture."""
    findings = await list_findings(db, limit=10_000)
    counts: dict[str, int] = {}
    for f in findings:
        if f.normalized_priority:
            counts[f.normalized_priority] = counts.get(f.normalized_priority, 0) + 1

    latest = await get_latest_assessment(db)
    if latest is None:
        return DashboardPayload(
            assessment=None,
            grade=None,
            criteria=CriteriaSnapshot(),
            findings_count_by_priority=counts,
            posture_pass_count=0,
            posture_total_count=0,
            completion_id=None,
        )

    posture_checks = await list_posture_checks_for_assessment(db, latest.id)
    pass_count = sum(1 for c in posture_checks if c.status == "pass")
    total_count = len(posture_checks)

    completion = await get_completion_for_assessment(db, latest.id)

    return DashboardPayload(
        assessment=latest,
        grade=latest.grade,
        criteria=latest.criteria_snapshot or CriteriaSnapshot(),
        findings_count_by_priority=counts,
        posture_pass_count=pass_count,
        posture_total_count=total_count,
        completion_id=completion.id if completion else None,
    )
