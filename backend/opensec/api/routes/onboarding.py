"""Onboarding routes (IMPL-0002 Milestone D1).

``POST /onboarding/repo`` persists the GitHub token (MVP: app_setting;
Session G can route this through the real credential vault) and kicks off an
initial assessment via the DI'd engine seam. ``POST /onboarding/complete`` flips
the ``onboarding.completed`` setting once the first assessment succeeds.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel

from opensec.api._background import schedule_assessment_run
from opensec.api._engine_dep import AssessmentEngineProtocol, get_assessment_engine
from opensec.db.connection import get_db
from opensec.db.dao.assessment import create_assessment, get_assessment
from opensec.db.repo_setting import upsert_setting
from opensec.models import AssessmentCreate

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingRepoRequest(BaseModel):
    repo_url: str
    github_token: str


class OnboardingRepoResponse(BaseModel):
    assessment_id: str
    repo_url: str


class OnboardingCompleteRequest(BaseModel):
    assessment_id: str


class OnboardingCompleteResponse(BaseModel):
    onboarding_completed: bool


@router.post("/repo", response_model=OnboardingRepoResponse)
async def connect_repo(
    request: OnboardingRepoRequest,
    http_request: FastAPIRequest,
    db=Depends(get_db),
    engine: AssessmentEngineProtocol = Depends(get_assessment_engine),
) -> OnboardingRepoResponse:
    """Register a repo and kick off the initial assessment."""
    repo_url = request.repo_url.strip()
    if not repo_url:
        raise HTTPException(status_code=422, detail="repo_url must not be empty")

    # MVP ad-hoc storage; Session G can route through the real credential vault.
    await upsert_setting(db, "onboarding.github_token", {"token": request.github_token})

    assessment = await create_assessment(db, AssessmentCreate(repo_url=repo_url))
    schedule_assessment_run(http_request.app, db, engine, assessment.id, repo_url)
    return OnboardingRepoResponse(assessment_id=assessment.id, repo_url=repo_url)


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    db=Depends(get_db),
) -> OnboardingCompleteResponse:
    """Mark onboarding as complete once the first assessment finishes."""
    assessment = await get_assessment(db, request.assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.status != "complete":
        raise HTTPException(
            status_code=409,
            detail=f"Assessment is '{assessment.status}', not 'complete'",
        )

    await upsert_setting(db, "onboarding.completed", {"completed": True})
    return OnboardingCompleteResponse(onboarding_completed=True)
