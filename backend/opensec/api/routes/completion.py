"""Completion routes (IMPL-0002 Milestone D5).

Fire-and-forget from the frontend; drives the v1.1 share-action rate metric.
Appends to ``completion.share_actions_used`` with insertion-order dedup so repeat
clicks don't skew the metric.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from opensec.db.connection import get_db
from opensec.db.dao.completion import record_share_action as dao_record_share_action
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
    db=Depends(get_db),
) -> ShareActionResponse:
    """Append the share action to the completion's audit row (idempotent)."""
    completion = await dao_record_share_action(db, completion_id, request.action)
    if completion is None:
        raise HTTPException(status_code=404, detail="Completion not found")
    return ShareActionResponse(
        completion_id=completion.id,
        share_actions_used=completion.share_actions_used,
    )
