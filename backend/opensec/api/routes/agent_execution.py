"""Agent execution endpoints — trigger, stream, cancel, suggest-next."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from opensec.agents.errors import AgentBusyError, AgentProcessError
from opensec.agents.pipeline import PIPELINE_ORDER, suggest_next
from opensec.db.connection import get_db
from opensec.db.repo_agent_run import get_agent_run, update_agent_run
from opensec.db.repo_workspace import get_workspace
from opensec.models import AgentRunUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-execution"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ExecuteResponse(BaseModel):
    agent_run_id: str
    agent_type: str
    status: str


class SuggestNextResponse(BaseModel):
    agent_type: str | None
    reason: str | None
    priority: str | None


# ---------------------------------------------------------------------------
# Execute agent
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/agents/{agent_type}/execute",
    response_model=ExecuteResponse,
    status_code=202,
)
async def execute_agent(
    workspace_id: str,
    agent_type: str,
    request: Request,
    db=Depends(get_db),
):
    """Start an agent run. Returns immediately with the agent_run_id.

    The execution runs as a background task. Use the SSE stream endpoint
    to follow progress.
    """
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not workspace.workspace_dir:
        raise HTTPException(status_code=400, detail="Workspace has no directory")

    if agent_type not in PIPELINE_ORDER:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid agent_type. Must be one of: {PIPELINE_ORDER}",
        )

    executor = request.app.state.agent_executor

    try:
        result = await executor.execute(
            workspace_id,
            agent_type,
            db,
            workspace_dir=workspace.workspace_dir,
        )
    except AgentBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AgentProcessError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ExecuteResponse(
        agent_run_id=result.agent_run_id,
        agent_type=result.agent_type,
        status=result.status,
    )


# ---------------------------------------------------------------------------
# Suggest next agent
# ---------------------------------------------------------------------------


@router.get(
    "/workspaces/{workspace_id}/pipeline/suggest-next",
    response_model=SuggestNextResponse,
)
async def suggest_next_endpoint(
    workspace_id: str,
    request: Request,
    db=Depends(get_db),
):
    """Return the recommended next agent based on current context state."""
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    context_builder = request.app.state.context_builder

    try:
        snapshot = await context_builder.get_context_snapshot(workspace_id)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Workspace directory not found"
        ) from exc

    run_history = snapshot.pop("agent_run_history", [])
    suggestion = suggest_next(snapshot, run_history)

    if suggestion is None:
        return SuggestNextResponse(
            agent_type=None, reason="Pipeline complete", priority=None
        )

    return SuggestNextResponse(
        agent_type=suggestion.agent_type,
        reason=suggestion.reason,
        priority=suggestion.priority,
    )


# ---------------------------------------------------------------------------
# Cancel running agent
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/agent-runs/{run_id}/cancel",
    status_code=200,
)
async def cancel_agent_run(
    workspace_id: str,
    run_id: str,
    db=Depends(get_db),
):
    """Cancel a running agent run."""
    run = await get_agent_run(db, run_id)
    if not run or run.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if run.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel agent run with status '{run.status}'",
        )

    await update_agent_run(
        db, run_id, AgentRunUpdate(status="cancelled")
    )
    return {"status": "cancelled", "agent_run_id": run_id}
