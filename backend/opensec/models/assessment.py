"""Assessment domain model (IMPL-0002 Milestone A).

An Assessment is one run of the deterministic scan engine against a repo. It
emits a list of Findings plus a set of PostureCheck results. The grade is
derived from five criteria at read-time; `criteria_snapshot` is only written to
persist the values at completion time.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import BaseModel

AssessmentStatus = Literal["pending", "running", "complete", "failed"]
Grade = Literal["A", "B", "C", "D", "F"]


class CriteriaSnapshot(BaseModel):
    """Five-criteria snapshot persisted at completion time.

    Values are derived at read-time elsewhere; this is the frozen record.
    """

    no_critical_vulns: bool = False
    posture_checks_passing: int = 0
    posture_checks_total: int = 0
    security_md_present: bool = False
    dependabot_present: bool = False


class AssessmentCreate(BaseModel):
    repo_url: str


class AssessmentUpdate(BaseModel):
    status: AssessmentStatus | None = None
    completed_at: datetime | None = None
    grade: Grade | None = None
    criteria_snapshot: CriteriaSnapshot | None = None


class Assessment(BaseModel):
    id: str
    repo_url: str
    started_at: datetime
    completed_at: datetime | None = None
    status: AssessmentStatus = "pending"
    grade: Grade | None = None
    criteria_snapshot: CriteriaSnapshot | None = None


class AssessmentResult(BaseModel):
    """Ephemeral return shape from the assessment engine (Session A).

    Route handlers in Session B call `run_assessment(repo_url) -> AssessmentResult`
    and persist the pieces to their respective tables.
    """

    assessment_id: str
    repo_url: str
    grade: Grade
    criteria_snapshot: CriteriaSnapshot
    findings: list[dict[str, Any]] = []
    posture_checks: list[dict[str, Any]] = []
