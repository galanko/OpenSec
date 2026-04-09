"""Workspace CRUD and workspace-scoped chat endpoints."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from opensec.api.tasks import fire_and_forget_send
from opensec.db.connection import get_db
from opensec.db.repo_finding import get_finding
from opensec.db.repo_workspace import (
    get_workspace,
    list_workspaces,
    update_workspace,
)
from opensec.models import Workspace, WorkspaceCreate, WorkspaceUpdate

if TYPE_CHECKING:
    from opensec.engine.pool import WorkspaceProcessPool
    from opensec.workspace.context_builder import WorkspaceContextBuilder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workspaces"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_pool(request: Request) -> WorkspaceProcessPool:
    return request.app.state.process_pool


def _get_context_builder(request: Request) -> WorkspaceContextBuilder:
    return request.app.state.context_builder


async def _get_workspace_or_404(db, workspace_id: str) -> Workspace:
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


@router.post("/workspaces", response_model=Workspace, status_code=201)
async def create_workspace_endpoint(
    body: WorkspaceCreate, request: Request, db=Depends(get_db)
):
    """Create a workspace with isolated directory and rendered agents."""
    context_builder = _get_context_builder(request)

    finding = await get_finding(db, body.finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")

    return await context_builder.create_workspace(
        db, finding, initial_focus=body.current_focus
    )


@router.get("/workspaces", response_model=list[Workspace])
async def list_workspaces_endpoint(
    state: str | None = None,
    finding_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
):
    return await list_workspaces(
        db, state=state, finding_id=finding_id, limit=limit, offset=offset
    )


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
async def get_workspace_endpoint(workspace_id: str, db=Depends(get_db)):
    return await _get_workspace_or_404(db, workspace_id)


@router.patch("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace_endpoint(
    workspace_id: str, body: WorkspaceUpdate, db=Depends(get_db)
):
    workspace = await update_workspace(db, workspace_id, body)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace_endpoint(
    workspace_id: str, request: Request, db=Depends(get_db)
):
    """Delete workspace: stop process, remove directory, delete DB row."""
    pool = _get_pool(request)
    await pool.stop(workspace_id)

    context_builder = _get_context_builder(request)
    deleted = await context_builder.delete_workspace(db, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found")


# ---------------------------------------------------------------------------
# Workspace-scoped sessions
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_id}/sessions")
async def create_workspace_session(
    workspace_id: str, request: Request, db=Depends(get_db)
):
    """Create an OpenCode session on this workspace's isolated process."""
    workspace = await _get_workspace_or_404(db, workspace_id)
    if not workspace.workspace_dir:
        raise HTTPException(status_code=409, detail="Workspace has no directory")

    pool = _get_pool(request)
    client = await pool.get_or_start(workspace_id, Path(workspace.workspace_dir))
    session = await client.create_session()
    return {"session_id": session.id, "workspace_id": workspace_id}


# ---------------------------------------------------------------------------
# Workspace-scoped chat
# ---------------------------------------------------------------------------


class WorkspaceChatRequest(BaseModel):
    session_id: str
    content: str


@router.post("/workspaces/{workspace_id}/chat/send")
async def workspace_send_message(
    workspace_id: str,
    body: WorkspaceChatRequest,
    request: Request,
    db=Depends(get_db),
):
    """Send a message to this workspace's OpenCode process."""
    workspace = await _get_workspace_or_404(db, workspace_id)
    if not workspace.workspace_dir:
        raise HTTPException(status_code=409, detail="Workspace has no directory")

    pool = _get_pool(request)
    client = await pool.get_or_start(workspace_id, Path(workspace.workspace_dir))

    fire_and_forget_send(client.send_message(body.session_id, body.content))
    return {"session_id": body.session_id, "status": "sent"}


@router.get("/workspaces/{workspace_id}/chat/stream")
async def workspace_stream_events(
    workspace_id: str,
    session_id: str,
    request: Request,
    db=Depends(get_db),
):
    """Stream SSE events from this workspace's OpenCode process."""
    workspace = await _get_workspace_or_404(db, workspace_id)
    if not workspace.workspace_dir:
        raise HTTPException(status_code=409, detail="Workspace has no directory")

    pool = _get_pool(request)
    client = await pool.get_or_start(workspace_id, Path(workspace.workspace_dir))

    async def event_generator():
        try:
            async for event in client.stream_events(session_id):
                event_type = event.get("type", "message")
                if event_type == "text":
                    yield {"event": "text", "data": event.get("content", "")}
                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps(
                            {"message": event.get("message", "Unknown error")}
                        ),
                    }
                elif event_type == "permission_request":
                    yield {
                        "event": "permission_request",
                        "data": json.dumps({
                            "id": event.get("id", ""),
                            "tool": event.get("tool", "unknown"),
                            "patterns": event.get("patterns", []),
                            "session_id": session_id,
                        }),
                    }
                elif event_type == "done":
                    yield {"event": "done", "data": "{}"}
                    return
        except Exception:
            logger.exception(
                "Error streaming for workspace %s session %s",
                workspace_id,
                session_id,
            )
            yield {
                "event": "error",
                "data": json.dumps({"message": "Stream disconnected"}),
            }

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Workspace-level permission approval (chat path)
# ---------------------------------------------------------------------------


class ChatPermissionDecision(BaseModel):
    permission_id: str
    session_id: str
    approved: bool


@router.post("/workspaces/{workspace_id}/chat/permission")
async def respond_to_chat_permission(
    workspace_id: str,
    body: ChatPermissionDecision,
    request: Request,
    db=Depends(get_db),
):
    """Approve or deny a permission request from the chat path.

    Unlike the agent-execution permission endpoint, this calls
    OpenCode's permission API directly (no executor involved).
    """
    workspace = await _get_workspace_or_404(db, workspace_id)
    if not workspace.workspace_dir:
        raise HTTPException(status_code=409, detail="Workspace has no directory")

    pool = _get_pool(request)
    client = await pool.get_or_start(workspace_id, Path(workspace.workspace_dir))

    try:
        if body.approved:
            await client.grant_permission(
                body.permission_id, session_id=body.session_id,
            )
        else:
            await client.deny_permission(
                body.permission_id, session_id=body.session_id,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to send permission decision to OpenCode: {exc}",
        ) from exc

    return {
        "status": "approved" if body.approved else "denied",
        "permission_id": body.permission_id,
    }


# ---------------------------------------------------------------------------
# Workspace context
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/context")
async def get_workspace_context(workspace_id: str, request: Request):
    """Return the full context snapshot for the sidebar."""
    context_builder = _get_context_builder(request)
    try:
        return await context_builder.get_context_snapshot(workspace_id)
    except FileNotFoundError:
        raise HTTPException(  # noqa: B904
            status_code=404, detail="Workspace directory not found"
        )


@router.get("/workspaces/{workspace_id}/pool-status")
async def workspace_pool_status(workspace_id: str, request: Request):
    """Debug endpoint: show process pool status for this workspace."""
    pool = _get_pool(request)
    full_status = pool.status()
    ws_status = full_status["workspaces"].get(workspace_id)
    if ws_status is None:
        return {"workspace_id": workspace_id, "process_running": False}
    return {"workspace_id": workspace_id, "process_running": True, **ws_status}


@router.get("/workspaces/{workspace_id}/integrations")
async def get_workspace_integrations(
    workspace_id: str, request: Request, db=Depends(get_db)
):
    """Return the active MCP integrations for a workspace with config freshness."""
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    integrations: list[dict] = []
    if workspace.workspace_dir:
        manifest_path = Path(workspace.workspace_dir) / "workspace-integrations.json"
        if manifest_path.exists():
            try:
                integrations = json.loads(manifest_path.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning(
                    "Failed to read workspace integrations manifest for %s",
                    workspace_id,
                )

    # Check config freshness if resolver is available.
    config_stale = False
    stale_reason = ""
    context_builder = _get_context_builder(request)
    resolver = getattr(context_builder, "_mcp_resolver", None)
    if resolver is not None and workspace.workspace_dir:
        try:
            freshness = await resolver.check_config_freshness(db, workspace.workspace_dir)
            config_stale = freshness.stale
            stale_reason = freshness.reason
        except Exception:
            logger.warning("Failed to check config freshness for %s", workspace_id)

    return {
        "integrations": integrations,
        "config_stale": config_stale,
        "stale_reason": stale_reason,
    }
