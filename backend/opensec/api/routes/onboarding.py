"""Onboarding routes.

``POST /onboarding/repo`` persists the GitHub token, probes the repo via the
GitHub REST API for display metadata, and kicks off an initial assessment via
the DI'd engine seam. ``POST /onboarding/complete`` flips the
``onboarding.completed`` setting once the first assessment succeeds.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPIRequest
from pydantic import BaseModel

from opensec.api._background import schedule_assessment_run
from opensec.api._engine_dep import (
    AssessmentEngineProtocol,
    get_assessment_engine,
    require_from_zero_to_secure_flag,
)
from opensec.assessment.posture.github_client import GithubClient, UnableToVerify
from opensec.db.connection import get_db
from opensec.db.dao.assessment import create_assessment, get_assessment
from opensec.db.repo_setting import upsert_setting
from opensec.models import AssessmentCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingRepoRequest(BaseModel):
    repo_url: str
    github_token: str


class VerifiedRepo(BaseModel):
    """Display-only metadata the SPA shows on the connect-success card."""

    repo_name: str
    visibility: str
    default_branch: str
    permissions: list[str] = []


class OnboardingRepoResponse(BaseModel):
    assessment_id: str
    repo_url: str
    verified: VerifiedRepo | None = None


def _parse_owner_repo(repo_url: str) -> tuple[str, str] | None:
    try:
        parsed = urlparse(repo_url)
    except ValueError:
        return None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None
    owner, name = parts[0], parts[1]
    if name.endswith(".git"):
        name = name[:-4]
    return owner, name


async def _probe_repo_metadata(
    repo_url: str, token: str
) -> VerifiedRepo | None:
    """Call the GitHub REST API for display metadata — never blocks the flow."""
    parsed = _parse_owner_repo(repo_url)
    if parsed is None:
        return None
    owner, name = parsed
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            client = GithubClient(http, token=token)
            info = await client.get_repo_info(owner, name)
    except Exception:  # pragma: no cover — defensive; client already swallows most
        logger.exception("GitHub metadata probe raised for %s/%s", owner, name)
        return None

    if isinstance(info, UnableToVerify):
        return None

    visibility = "private" if info.get("private") else "public"
    raw_perms = info.get("permissions") or {}
    perms = sorted(k for k, v in raw_perms.items() if v) if isinstance(raw_perms, dict) else []
    return VerifiedRepo(
        repo_name=info.get("full_name") or f"{owner}/{name}",
        visibility=visibility,
        default_branch=info.get("default_branch") or "main",
        permissions=perms,
    )


class OnboardingCompleteRequest(BaseModel):
    assessment_id: str


class OnboardingCompleteResponse(BaseModel):
    onboarding_completed: bool


@router.post(
    "/repo",
    response_model=OnboardingRepoResponse,
    dependencies=[Depends(require_from_zero_to_secure_flag)],
)
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

    # MVP ad-hoc storage; routing through the credential vault is follow-up work.
    await upsert_setting(db, "onboarding.github_token", {"token": request.github_token})

    verified = await _probe_repo_metadata(repo_url, request.github_token)

    assessment = await create_assessment(db, AssessmentCreate(repo_url=repo_url))
    schedule_assessment_run(http_request.app, db, engine, assessment.id, repo_url)
    return OnboardingRepoResponse(
        assessment_id=assessment.id, repo_url=repo_url, verified=verified
    )


@router.post(
    "/complete",
    response_model=OnboardingCompleteResponse,
    dependencies=[Depends(require_from_zero_to_secure_flag)],
)
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
