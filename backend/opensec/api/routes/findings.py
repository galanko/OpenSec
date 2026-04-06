"""Finding CRUD endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from opensec.db.connection import get_db
from opensec.db.repo_finding import (
    create_finding,
    delete_finding,
    get_finding,
    list_findings,
    update_finding,
)
from opensec.integrations.normalizer import normalize_findings
from opensec.models import Finding, FindingCreate, FindingUpdate, IngestRequest, IngestResult

logger = logging.getLogger(__name__)

router = APIRouter(tags=["findings"])


@router.post("/findings", response_model=Finding, status_code=201)
async def create_finding_endpoint(body: FindingCreate, db=Depends(get_db)):
    return await create_finding(db, body)


@router.get("/findings", response_model=list[Finding])
async def list_findings_endpoint(
    status: str | None = None,
    has_workspace: bool | None = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
):
    return await list_findings(
        db, status=status, has_workspace=has_workspace, limit=limit, offset=offset,
    )


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


@router.post("/findings/ingest", response_model=IngestResult)
async def ingest_findings_endpoint(body: IngestRequest, db=Depends(get_db)):
    """Normalize raw scanner findings via LLM and create Finding records.

    Accepts raw data from any scanner format. The LLM extracts structured
    fields into FindingCreate schema. See ADR-0022.
    """
    valid, errors = await normalize_findings(body.source, body.raw_data)

    created: list[Finding] = []
    for fc in valid:
        try:
            finding = await create_finding(db, fc)
            created.append(finding)
        except Exception as exc:
            logger.warning("Failed to persist normalized finding: %s", exc)
            errors.append(f"DB error: {exc}")

    return IngestResult(created=created, errors=errors)
