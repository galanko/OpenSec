"""Completion routes (IMPL-0002 Milestone D5).

Session-0 contract stub. Fire-and-forget from the frontend; drives the v1.1
share-action rate metric.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from opensec.models import ShareAction

router = APIRouter(prefix="/completion", tags=["completion"])


class ShareActionRequest(BaseModel):
    action: ShareAction


class ShareActionResponse(BaseModel):
    completion_id: str
    share_actions_used: list[ShareAction]


@router.post("/{completion_id}/share-action", response_model=ShareActionResponse)
async def record_share_action(
    completion_id: str,
    request: ShareActionRequest,
) -> ShareActionResponse:
    """Append the share action to the completion's audit row (idempotent)."""
    raise NotImplementedError("Session 0 stub — implemented in Session B")
