"""Posture routes (IMPL-0002 Milestone D3).

Spawns a repo-workspace via ``RepoWorkspaceSpawnerProtocol`` (Session C wires the
real spawner in Session G via the DI seam in ``opensec.api._engine_dep``). The
response returns the workspace id so the UI can poll sidebar state for PR url +
status.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from opensec.api._engine_dep import (
    RepoWorkspaceSpawnerProtocol,
    get_repo_workspace_spawner,
)
from opensec.config import settings
from opensec.db.connection import get_db
from opensec.db.dao.assessment import get_latest_assessment
from opensec.workspace.repo_workspace_runner import (
    RepoAgentStatus,
    read_status,
)
from opensec.workspace.workspace_dir_manager import WorkspaceKind

router = APIRouter(prefix="/posture", tags=["posture"])

PostureFixCheckName = Literal["security_md", "dependabot_config"]


class PostureFixRequest(BaseModel):
    """Optional per-check parameters the UI can send with the fix call.

    All fields are optional — the template falls back to clearly-labelled
    placeholders when a value is missing. We accept the full set up-front so
    adding a new field (e.g. ``contact_url``) later doesn't require a new
    request model.
    """

    contact_email: str | None = None
    contact_url: str | None = None
    supported_versions: str | None = None
    disclosure_window_days: int | None = None


class PostureFixResponse(BaseModel):
    workspace_id: str
    check_name: PostureFixCheckName


_CHECK_TO_WORKSPACE_KIND: dict[PostureFixCheckName, WorkspaceKind] = {
    "security_md": WorkspaceKind.repo_action_security_md,
    "dependabot_config": WorkspaceKind.repo_action_dependabot,
}


@router.post("/fix/{check_name}", response_model=PostureFixResponse)
async def fix_posture_check(
    check_name: PostureFixCheckName,
    body: PostureFixRequest | None = None,
    db=Depends(get_db),
    spawner: RepoWorkspaceSpawnerProtocol = Depends(get_repo_workspace_spawner),
) -> PostureFixResponse:
    """Spawn a repo-workspace with the appropriate generator agent.

    ``body`` is optional: existing callers that POST an empty body still work
    and the generator templates fall back to placeholders. When the UI sends
    ``contact_email`` (or other template params), we thread them through the
    spawner so the rendered prompt substitutes them verbatim and the
    maintainer gets a PR that needs fewer edits.
    """
    latest = await get_latest_assessment(db)
    if latest is None:
        raise HTTPException(
            status_code=409, detail="No repo registered — run an assessment first"
        )

    params = body.model_dump(exclude_none=True) if body else {}
    workspace_id = await spawner.spawn_repo_workspace(
        kind=_CHECK_TO_WORKSPACE_KIND[check_name],
        repo_url=latest.repo_url,
        params=params or None,
    )
    return PostureFixResponse(workspace_id=workspace_id, check_name=check_name)


# Path-component sanity: workspace ids are 20+ chars of hex and an explicit
# kind prefix. A leading slash or ``..`` would be caught by FastAPI's path
# matching already but we belt-and-braces reject it.
_BAD_ID_CHARS = frozenset({"/", "\\"})


@router.get("/fix/status/{workspace_id}", response_model=RepoAgentStatus)
async def get_posture_fix_status(workspace_id: str) -> RepoAgentStatus:
    """Return the current status of a posture-fix agent run.

    Polled by the UI after ``POST /posture/fix/{check_name}`` returns a
    workspace id. Reads from ``data/workspaces/<id>/history/status.json``
    — no DB involvement; status is workspace-local state.
    """
    if not workspace_id or any(c in _BAD_ID_CHARS for c in workspace_id):
        raise HTTPException(status_code=400, detail="Invalid workspace id")
    if ".." in workspace_id.split("/"):
        raise HTTPException(status_code=400, detail="Invalid workspace id")

    workspace_root = settings.resolve_data_dir() / "workspaces" / workspace_id
    if not workspace_root.is_dir():
        raise HTTPException(status_code=404, detail="Workspace not found")

    status = read_status(workspace_root)
    if status is None:
        # Directory exists but the runner hasn't written an initial status
        # yet. Return a synthetic "queued" so the UI doesn't have to model
        # the missing-file case separately.
        return RepoAgentStatus(
            workspace_id=workspace_id,
            kind="unknown",
            status="queued",
            started_at="",
        )
    return status
