"""Assessment routes (IMPL-0002 Milestone D2).

``POST /assessment/run`` creates a ``pending`` row and schedules the engine as a
background task. ``GET /assessment/status/{id}`` polls the current state (SSE
upgrade is deferred to Session G per the Session-0 stub comment). ``GET
/assessment/latest`` returns the most recent assessment's report-card shape.

The engine is injected via ``get_assessment_engine``; Session A/G swap the real
implementation behind the same DI seam.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel

from opensec.api._engine_dep import AssessmentEngineProtocol, get_assessment_engine
from opensec.db.connection import get_db
from opensec.db.dao.assessment import (
    create_assessment,
    get_assessment,
    set_assessment_result,
    update_assessment,
)
from opensec.db.dao.assessment import (
    get_latest_assessment as dao_get_latest_assessment,
)
from opensec.db.dao.completion import (
    create_completion,
    get_completion_for_assessment,
)
from opensec.db.dao.posture_check import (
    list_posture_checks_for_assessment,
    upsert_posture_check,
)
from opensec.db.repo_finding import list_findings
from opensec.models import (
    Assessment,
    AssessmentCreate,
    AssessmentUpdate,
    CompletionCreate,
    CriteriaSnapshot,
    Grade,
    PostureCheckCreate,
)

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)

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


_STATUS_TO_PROGRESS: dict[str, int] = {
    "pending": 0,
    "running": 50,
    "complete": 100,
    "failed": 0,
}


def _criteria_all_met(c: CriteriaSnapshot) -> bool:
    return (
        c.no_critical_vulns
        and c.security_md_present
        and c.dependabot_present
        and c.posture_checks_total > 0
        and c.posture_checks_passing == c.posture_checks_total
    )


async def _run_and_persist(
    db: aiosqlite.Connection,
    engine: AssessmentEngineProtocol,
    assessment_id: str,
    repo_url: str,
) -> None:
    """Run the engine and persist results. Owns its own try/except."""
    try:
        await update_assessment(db, assessment_id, AssessmentUpdate(status="running"))
        result = await engine.run_assessment(repo_url, assessment_id=assessment_id)
    except Exception:
        logger.exception("assessment engine failed for %s", assessment_id)
        await update_assessment(db, assessment_id, AssessmentUpdate(status="failed"))
        return

    # Posture checks: upsert each one (idempotent across re-runs).
    for check in result.posture_checks:
        await upsert_posture_check(
            db,
            PostureCheckCreate(
                assessment_id=assessment_id,
                check_name=check["check_name"],
                status=check["status"],
                detail=check.get("detail"),
            ),
        )

    await set_assessment_result(
        db, assessment_id, grade=result.grade, criteria_snapshot=result.criteria_snapshot
    )

    # Completion row — only when every criterion is met (ADR-0025 derived state).
    if _criteria_all_met(result.criteria_snapshot):
        existing = await get_completion_for_assessment(db, assessment_id)
        if existing is None:
            await create_completion(
                db,
                CompletionCreate(
                    assessment_id=assessment_id,
                    repo_url=repo_url,
                    criteria_snapshot=result.criteria_snapshot,
                ),
            )


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

    # Schedule the engine in the background so the POST returns quickly. We keep
    # the task reference on app.state so tests can drain before asserting and so
    # the lifespan can gather during shutdown.
    task = asyncio.create_task(
        _run_and_persist(db, engine, assessment.id, request.repo_url)
    )
    tasks: list[asyncio.Task] = getattr(http_request.app.state, "assessment_tasks", [])
    tasks.append(task)
    http_request.app.state.assessment_tasks = tasks

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
        # Still running — no report card available.
        raise HTTPException(status_code=409, detail="Latest assessment is not yet complete")

    checks = await list_posture_checks_for_assessment(db, latest.id)
    pass_count = sum(1 for c in checks if c.status == "pass")

    findings = await list_findings(db, limit=10_000)
    counts: dict[str, int] = {}
    for f in findings:
        if f.normalized_priority:
            counts[f.normalized_priority] = counts.get(f.normalized_priority, 0) + 1

    return AssessmentLatestResponse(
        assessment=latest,
        grade=latest.grade,
        criteria=latest.criteria_snapshot or CriteriaSnapshot(),
        findings_count_by_priority=counts,
        posture_pass_count=pass_count,
        posture_total_count=len(checks),
    )


