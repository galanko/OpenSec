"""Assessment routes (IMPL-0002 Milestone D2).

``POST /assessment/run`` creates a ``pending`` row and schedules the engine as a
background task. ``GET /assessment/status/{id}`` polls the current state (SSE
upgrade is deferred to Session G per the Session-0 stub comment). ``GET
/assessment/latest`` returns the most recent assessment's report-card shape.

The engine is injected via ``get_assessment_engine``; Session A/G swap the real
implementation behind the same DI seam.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel

from opensec.api._background import schedule_assessment_run
from opensec.api._engine_dep import AssessmentEngineProtocol, get_assessment_engine
from opensec.db.connection import get_db
from opensec.db.dao.assessment import create_assessment, get_assessment
from opensec.db.dao.assessment import (
    get_latest_assessment as dao_get_latest_assessment,
)
from opensec.db.dao.posture_check import count_posture_pass_total
from opensec.db.repo_finding import count_findings_by_priority
from opensec.models import (
    Assessment,
    AssessmentCreate,
    AssessmentStatus,
    CriteriaSnapshot,
    Grade,
)

router = APIRouter(prefix="/assessment", tags=["assessment"])


class AssessmentRunResponse(BaseModel):
    assessment_id: str
    status: str


class AssessmentStatusResponse(BaseModel):
    assessment_id: str
    status: str
    progress_pct: int
    step: str | None = None


class AssessmentLatestResponse(BaseModel):
    assessment: Assessment
    grade: Grade
    criteria: CriteriaSnapshot
    findings_count_by_priority: dict[str, int]
    posture_pass_count: int
    posture_total_count: int


_STATUS_TO_PROGRESS: dict[AssessmentStatus, int] = {
    "pending": 0,
    "running": 50,
    "complete": 100,
    "failed": 0,
}


@router.post("/run", response_model=AssessmentRunResponse)
async def run_assessment(
    request: AssessmentCreate,
    http_request: FastAPIRequest,
    db=Depends(get_db),
    engine: AssessmentEngineProtocol = Depends(get_assessment_engine),
) -> AssessmentRunResponse:
    """Start a new assessment for the given repo."""
    if not request.repo_url.strip():
        raise HTTPException(status_code=422, detail="repo_url must not be empty")

    assessment = await create_assessment(db, request)
    schedule_assessment_run(
        http_request.app, db, engine, assessment.id, request.repo_url
    )
    return AssessmentRunResponse(assessment_id=assessment.id, status="pending")


@router.get("/status/{assessment_id}", response_model=AssessmentStatusResponse)
async def get_assessment_status(
    assessment_id: str, db=Depends(get_db)
) -> AssessmentStatusResponse:
    """Poll assessment progress. Session B will upgrade this to SSE."""
    a = await get_assessment(db, assessment_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return AssessmentStatusResponse(
        assessment_id=a.id,
        status=a.status,
        progress_pct=_STATUS_TO_PROGRESS.get(a.status, 0),
        step=a.status,
    )


@router.get("/latest", response_model=AssessmentLatestResponse)
async def get_latest_assessment(db=Depends(get_db)) -> AssessmentLatestResponse:
    """Report-card payload for the dashboard."""
    latest = await dao_get_latest_assessment(db)
    if latest is None:
        raise HTTPException(status_code=404, detail="No assessments yet")
    if latest.grade is None:
        raise HTTPException(status_code=409, detail="Latest assessment is not yet complete")

    pass_count, total_count = await count_posture_pass_total(db, latest.id)
    counts = await count_findings_by_priority(db)

    return AssessmentLatestResponse(
        assessment=latest,
        grade=latest.grade,
        criteria=latest.criteria_snapshot or CriteriaSnapshot(),
        findings_count_by_priority=counts,
        posture_pass_count=pass_count,
        posture_total_count=total_count,
    )
