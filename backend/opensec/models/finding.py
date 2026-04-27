"""Finding domain model (PRD-0003 v0.2 / ADR-0027).

A Finding is anything in the user's security backlog: a vulnerable dependency,
a leaked secret, a SAST hit, a posture check (pass / fail / advisory). Every
producer (Trivy, Semgrep, the posture orchestrator, the LLM normalizer for
external scanner payloads) maps to ``FindingCreate`` and persists through the
same UPSERT path on ``(source_type, source_id)``.

The ``type`` taxonomy is the semantic category (``dependency`` / ``code`` /
``secret`` / ``posture``); ``source_type`` is the producer-of-record. Trivy
emits both ``type='dependency'`` (vuln scan) and ``type='secret'`` (secret
scan) under different ``source_type`` values (``trivy`` and ``trivy-secret``)
so the stale-close pass can scope correctly.

``status`` carries the user lifecycle for non-posture findings (preserved
across rescans), and the scanner-reported state for ``type='posture'`` rows
(refreshed on every scan because the scanner is the source of truth). The
``'passed'`` status is reserved for posture rows that the latest scan
reports as passing.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import BaseModel

FindingStatus = Literal[
    "new",
    "triaged",
    "in_progress",
    "remediated",
    "validated",
    "closed",
    "exception",
    # PRD-0003 v0.2 / ADR-0027 §unified — scanner reports this posture
    # check as currently passing. For non-posture types, ``status`` is a
    # user-lifecycle state preserved across rescans; for ``type='posture'``
    # it tracks scanner truth and is refreshed on every UPSERT.
    "passed",
]

#: Semantic category. Both Trivy vuln + secret scans land under different
#: ``source_type`` values ("trivy", "trivy-secret") with corresponding
#: ``type`` values ("dependency", "secret"); the close pass scopes by
#: ``source_type``, the dashboard filters by ``type``.
FindingType = Literal["dependency", "code", "secret", "posture"]

#: ``counts`` findings count toward the ten-criterion grade. ``advisory``
#: rows are informational and excluded from the dashboard's progress rail.
FindingGradeImpact = Literal["counts", "advisory"]


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
    # ADR-0027 v0.2 columns.
    type: FindingType = "dependency"
    grade_impact: FindingGradeImpact = "counts"
    category: str | None = None
    assessment_id: str | None = None
    pr_url: str | None = None


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
    type: FindingType | None = None
    grade_impact: FindingGradeImpact | None = None
    category: str | None = None
    assessment_id: str | None = None
    pr_url: str | None = None


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
    type: FindingType = "dependency"
    grade_impact: FindingGradeImpact = "counts"
    category: str | None = None
    assessment_id: str | None = None
    pr_url: str | None = None
    created_at: datetime
    updated_at: datetime
