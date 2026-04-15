"""Finding domain model.

A Finding is a vulnerability surfaced by a scanner (or ingested from a CSV/JSON
payload). `plain_description` (IMPL-0002 Milestone C) is populated by the
finding-normalizer agent with 2–4 sentences of jargon-free guidance ending in a
fix hint.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import BaseModel

FindingStatus = Literal[
    "new", "triaged", "in_progress", "remediated", "validated", "closed", "exception"
]


class FindingCreate(BaseModel):
    source_type: str
    source_id: str
    title: str
    description: str | None = None
    plain_description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus = "new"
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    plain_description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus | None = None
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None


class Finding(BaseModel):
    id: str
    source_type: str
    source_id: str
    title: str
    description: str | None = None
    plain_description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus = "new"
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
