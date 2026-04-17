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
from opensec.db.repo_integration import (
    create_integration,
    list_integrations,
    update_integration,
)
from opensec.db.repo_setting import upsert_setting
from opensec.models import (
    AssessmentCreate,
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
)

# ``upsert_setting`` is still used by ``/complete`` (``onboarding.completed``).

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


GITHUB_ADAPTER_TYPE = "github"
GITHUB_PROVIDER_NAME = "GitHub"
# Canonical credential key name, matched by the GitHub registry entry
# (backend/opensec/integrations/registry/github.json) and read by the
# remediation executor's workspace setup + the connection tester. Writing
# under any other name silently breaks "open a PR" remediation.
GITHUB_TOKEN_KEY = "github_personal_access_token"


async def _upsert_github_integration(
    db,
    http_request: FastAPIRequest,
    token: str,
    repo_url: str,
    verified: VerifiedRepo | None,
) -> None:
    """Single source of truth for the onboarding PAT.

    Writes the GitHub integration row + credential through the same path the
    Integrations settings page uses, so "solve a finding" sees the PAT that
    onboarding just collected. Idempotent: reruns update the existing row
    instead of creating a duplicate.
    """
    integrations = await list_integrations(db)
    existing = next(
        (i for i in integrations if i.adapter_type == GITHUB_ADAPTER_TYPE), None
    )

    config = {
        "repo_url": repo_url,
        "default_branch": verified.default_branch if verified else None,
        "repo_name": verified.repo_name if verified else None,
    }

    if existing is None:
        integration = await create_integration(
            db,
            IntegrationConfigCreate(
                adapter_type=GITHUB_ADAPTER_TYPE,
                provider_name=GITHUB_PROVIDER_NAME,
                config=config,
                action_tier=2,
            ),
        )
    else:
        integration = await update_integration(
            db,
            existing.id,
            IntegrationConfigUpdate(enabled=True, config=config, action_tier=2),
        )
        assert integration is not None

    vault = getattr(http_request.app.state, "vault", None)
    if vault is None:
        # No vault in this deployment — the token is lost. Logged loudly so
        # operators know to set OPENSEC_CREDENTIAL_KEY. The Integrations row
        # still exists; they can re-enter the PAT from Settings.
        logger.warning(
            "credential vault not initialized; GitHub PAT from onboarding was not stored. "
            "Set OPENSEC_CREDENTIAL_KEY to enable durable credential storage."
        )
        return

    await vault.store(integration.id, GITHUB_TOKEN_KEY, token)


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

    verified = await _probe_repo_metadata(repo_url, request.github_token)

    # Store the PAT through the same path the Integrations settings page uses —
    # single source of truth. "Solve a finding" + posture-fix spawner both
    # read from this row later.
    await _upsert_github_integration(
        db, http_request, request.github_token, repo_url, verified
    )

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
