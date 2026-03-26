"""Workspace CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from opensec.db.connection import get_db
from opensec.db.repo_workspace import (
    create_workspace,
    delete_workspace,
    get_workspace,
    list_workspaces,
    update_workspace,
)
from opensec.models import Workspace, WorkspaceCreate, WorkspaceUpdate

router = APIRouter(tags=["workspaces"])


@router.post("/workspaces", response_model=Workspace, status_code=201)
async def create_workspace_endpoint(body: WorkspaceCreate, db=Depends(get_db)):
    return await create_workspace(db, body)


@router.get("/workspaces", response_model=list[Workspace])
async def list_workspaces_endpoint(
    state: str | None = None,
    finding_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
):
    return await list_workspaces(db, state=state, finding_id=finding_id, limit=limit, offset=offset)


@router.get("/workspaces/{workspace_id}", response_model=Workspace)
async def get_workspace_endpoint(workspace_id: str, db=Depends(get_db)):
    workspace = await get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.patch("/workspaces/{workspace_id}", response_model=Workspace)
async def update_workspace_endpoint(
    workspace_id: str, body: WorkspaceUpdate, db=Depends(get_db)
):
    workspace = await update_workspace(db, workspace_id, body)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_workspace_endpoint(workspace_id: str, db=Depends(get_db)):
    deleted = await delete_workspace(db, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workspace not found")
