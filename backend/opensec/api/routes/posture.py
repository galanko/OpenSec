"""Posture routes (IMPL-0002 Milestone D3).

Session-0 contract stub. Real implementation spawns a repo-workspace via
``WorkspaceDirManager.create_repo_workspace`` (Session C) and returns its id so
the UI can poll sidebar state.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/posture", tags=["posture"])

PostureFixCheckName = Literal["security_md", "dependabot_config"]


class PostureFixResponse(BaseModel):
    workspace_id: str
    check_name: PostureFixCheckName


@router.post("/fix/{check_name}", response_model=PostureFixResponse)
async def fix_posture_check(check_name: PostureFixCheckName) -> PostureFixResponse:
    """Spawn a repo-workspace with the appropriate generator agent."""
    raise NotImplementedError("Session 0 stub — implemented in Session B + C")
