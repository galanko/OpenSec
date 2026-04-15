"""Assessment routes (IMPL-0002 Milestone D2).

Session-0 contract stub. Real implementation ships in Session B. The SSE
status endpoint is declared as a regular GET that returns a summary response
shape; Session B will swap the implementation for a real EventSourceResponse
while keeping the path + query parameters stable.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from opensec.models import Assessment, AssessmentCreate, CriteriaSnapshot, Grade

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


@router.post("/run", response_model=AssessmentRunResponse)
async def run_assessment(request: AssessmentCreate) -> AssessmentRunResponse:
    """Start a new assessment for the given repo."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")


@router.get("/status/{assessment_id}", response_model=AssessmentStatusResponse)
async def get_assessment_status(assessment_id: str) -> AssessmentStatusResponse:
    """Poll assessment progress. Session B will upgrade this to SSE."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")


@router.get("/latest", response_model=AssessmentLatestResponse)
async def get_latest_assessment() -> AssessmentLatestResponse:
    """Report-card payload for the dashboard."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")
