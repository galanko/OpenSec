"""Agent execution endpoints — trigger, stream, cancel, suggest-next."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

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
# Agent chips (UI metadata)
# ---------------------------------------------------------------------------


class AgentChipResponse(BaseModel):
    agent_type: str
    label: str
    icon: str


@router.get("/agents/chips", response_model=list[AgentChipResponse])
async def list_agent_chips():
    """Return the ordered list of action chips for the UI."""
    from opensec.agents.registry import AGENT_CHIPS

    return [
        AgentChipResponse(agent_type=c.agent_type, label=c.label, icon=c.icon)
        for c in AGENT_CHIPS
    ]


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
    """Start an agent run as a background task.

    Returns immediately with the agent_run_id. Connect to the
    agent-execution SSE stream to receive permission_request events
    and a done signal.
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

    # Pre-flight check: fail fast if another agent is already running.
    try:
        await executor.check_not_busy(db, workspace_id)
    except AgentBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Launch execution as a background task so we can return immediately.
    async def _run_in_background() -> None:
        try:
            await executor.execute(
                workspace_id,
                agent_type,
                db,
                workspace_dir=workspace.workspace_dir,
                on_permission=lambda evt: executor.push_permission_event(
                    workspace_id, evt
                ),
            )
        except (AgentBusyError, AgentProcessError):
            logger.exception(
                "Agent execution failed for workspace %s", workspace_id
            )
        except Exception:
            logger.exception(
                "Unexpected error in background agent execution for workspace %s",
                workspace_id,
            )

    asyncio.create_task(_run_in_background())

    # Wait for execute() to register the run ID (set at the top of execute()).
    # Uses a short-polling loop instead of a fixed sleep to avoid races.
    for _ in range(10):
        await asyncio.sleep(0.01)
        run_id = executor.get_active_run_id(workspace_id)
        if run_id:
            break
    else:
        run_id = "pending"

    return ExecuteResponse(
        agent_run_id=run_id or "pending",
        agent_type=agent_type,
        status="running",
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


# ---------------------------------------------------------------------------
# Permission approval
# ---------------------------------------------------------------------------


class PermissionDecision(BaseModel):
    approved: bool


@router.post(
    "/workspaces/{workspace_id}/agent-runs/{run_id}/permission",
    status_code=200,
)
async def respond_to_permission(
    workspace_id: str,
    run_id: str,
    body: PermissionDecision,
    request: Request,
):
    """Approve or deny a pending tool-use permission request."""
    executor = request.app.state.agent_executor

    resolved = (
        executor.approve_tool(run_id)
        if body.approved
        else executor.deny_tool(run_id)
    )

    if not resolved:
        raise HTTPException(
            status_code=404,
            detail="No pending permission request for this agent run",
        )

    return {
        "status": "approved" if body.approved else "denied",
        "agent_run_id": run_id,
    }


# ---------------------------------------------------------------------------
# Agent execution SSE stream
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/agent-execution/stream")
async def stream_agent_execution(
    workspace_id: str,
    request: Request,
):
    """Stream permission_request and done events during agent execution.

    The frontend connects to this while an agent is running. Events:
    - permission_request: agent needs user approval for a tool
    - done: agent execution has completed (success or failure)

    If the client disconnects while a permission is pending, the pending
    approval is auto-denied to unblock the executor.
    """
    executor = request.app.state.agent_executor

    async def event_generator():
        queue = executor.get_permission_queue(workspace_id)
        if not queue:
            # No active execution — send done immediately
            yield {"event": "done", "data": "{}"}
            return

        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    # Auto-deny any pending approval to unblock executor
                    run_id = executor.get_active_run_id(workspace_id)
                    if run_id:
                        executor.deny_tool(run_id)
                        logger.info(
                            "Client disconnected, auto-denied permission "
                            "for workspace %s run %s",
                            workspace_id, run_id,
                        )
                    return

                # Poll queue with timeout to allow disconnect checks
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=2.0)
                except TimeoutError:
                    continue

                event_type = event.get("type", "permission_request")
                if event_type == "done":
                    yield {"event": "done", "data": "{}"}
                    return
                else:
                    yield {
                        "event": "permission_request",
                        "data": json.dumps({
                            "id": event.get("id", ""),
                            "tool": event.get("tool", "unknown"),
                            "patterns": event.get("patterns", []),
                            "run_id": event.get("run_id", ""),
                        }),
                    }
        except Exception:
            logger.exception(
                "Error in agent execution stream for workspace %s",
                workspace_id,
            )
            yield {
                "event": "error",
                "data": json.dumps({"message": "Stream disconnected"}),
            }

    return EventSourceResponse(event_generator())
