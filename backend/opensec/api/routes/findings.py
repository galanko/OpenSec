"""Finding CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from opensec.db.connection import get_db
from opensec.db.repo_finding import (
    create_finding,
    delete_finding,
    get_finding,
    list_findings,
    update_finding,
)
from opensec.models import Finding, FindingCreate, FindingUpdate

router = APIRouter(tags=["findings"])


@router.post("/findings", response_model=Finding, status_code=201)
async def create_finding_endpoint(body: FindingCreate, db=Depends(get_db)):
    return await create_finding(db, body)


@router.get("/findings", response_model=list[Finding])
async def list_findings_endpoint(
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
):
    return await list_findings(db, status=status, limit=limit, offset=offset)


@router.get("/findings/{finding_id}", response_model=Finding)
async def get_finding_endpoint(finding_id: str, db=Depends(get_db)):
    finding = await get_finding(db, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.patch("/findings/{finding_id}", response_model=Finding)
async def update_finding_endpoint(finding_id: str, body: FindingUpdate, db=Depends(get_db)):
    finding = await update_finding(db, finding_id, body)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.delete("/findings/{finding_id}", status_code=204)
async def delete_finding_endpoint(finding_id: str, db=Depends(get_db)):
    deleted = await delete_finding(db, finding_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Finding not found")
