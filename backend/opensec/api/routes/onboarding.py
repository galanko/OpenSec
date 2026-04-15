"""Onboarding routes (IMPL-0002 Milestone D1).

Session-0 contract stub. Real implementation ships in Session B. Each body
raises ``NotImplementedError`` so the OpenAPI schema is frozen but no real
work happens yet.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

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
async def connect_repo(request: OnboardingRepoRequest) -> OnboardingRepoResponse:
    """Register a repo and kick off the initial assessment."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")


@router.post("/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
) -> OnboardingCompleteResponse:
    """Mark onboarding as complete once the first assessment finishes."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")
