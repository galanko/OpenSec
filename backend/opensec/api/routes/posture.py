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
from opensec.db.connection import get_db
from opensec.db.dao.assessment import get_latest_assessment

router = APIRouter(prefix="/posture", tags=["posture"])

PostureFixCheckName = Literal["security_md", "dependabot_config"]


class PostureFixResponse(BaseModel):
    workspace_id: str
    check_name: PostureFixCheckName


_CHECK_TO_WORKSPACE_KIND: dict[PostureFixCheckName, str] = {
    "security_md": "repo_action_security_md",
    "dependabot_config": "repo_action_dependabot",
}


@router.post("/fix/{check_name}", response_model=PostureFixResponse)
async def fix_posture_check(
    check_name: PostureFixCheckName,
    db=Depends(get_db),
    spawner: RepoWorkspaceSpawnerProtocol = Depends(get_repo_workspace_spawner),
) -> PostureFixResponse:
    """Spawn a repo-workspace with the appropriate generator agent."""
    latest = await get_latest_assessment(db)
    if latest is None:
        raise HTTPException(
            status_code=409, detail="No repo registered — run an assessment first"
        )

    workspace_id = await spawner.spawn_repo_workspace(
        kind=_CHECK_TO_WORKSPACE_KIND[check_name], repo_url=latest.repo_url
    )
    return PostureFixResponse(workspace_id=workspace_id, check_name=check_name)
