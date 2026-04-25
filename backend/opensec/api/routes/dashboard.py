"""Dashboard routes (PRD-0003 v0.2 / ADR-0032).

Read-only aggregation over the latest assessment, the posture sweep, finding
priority counts, and (if any) completion row. The wire shape exposes the v0.2
contract: a single ``tools[]`` payload (no parallel ``scanner_versions`` /
``tool_states[]``), a four-state posture vocabulary (``pass | fail | done |
advisory``) with per-category progress that excludes advisory rows, the labeled
``criteria[]`` list, vulnerability counts split by source, and the
``summary_seen_at`` flag that gates the assessment-complete interstitial.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from opensec.assessment.posture import (
    ADVISORY_CHECKS,
    CHECK_CATEGORY,
    CHECK_DISPLAY_NAME,
)
from opensec.db.connection import get_db
from opensec.db.dao.assessment import get_latest_assessment
from opensec.db.dao.completion import get_completion_for_assessment
from opensec.db.dao.posture_check import (
    count_posture_pass_total,
    list_posture_checks_for_assessment,
)
from opensec.db.repo_finding import count_findings_by_priority, list_findings
from opensec.models import (
    Assessment,
    AssessmentTool,
    AssessmentToolResult,
    CriteriaSnapshot,
    Grade,
    PostureCheck,
    PostureCheckCategory,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


PostureWireState = Literal["pass", "fail", "done", "advisory"]


# --------------------------------------------------------------------- payload
class CriterionLabel(BaseModel):
    """One row of the labeled ``criteria[]`` list (ADR-0032 §1.4)."""

    key: str
    label: str
    met: bool


class PostureCheckWire(BaseModel):
    name: str
    display_name: str
    category: PostureCheckCategory
    state: PostureWireState
    grade_impact: Literal["counts", "advisory"]
    fixable_by: str | None = None
    detail: str | None = None
    pr_url: str | None = None


class CategoryProgress(BaseModel):
    done: int
    total: int


class PostureCategoryWire(BaseModel):
    name: PostureCheckCategory
    display_name: str
    progress: CategoryProgress
    checks: list[PostureCheckWire]


class PostureWire(BaseModel):
    pass_count: int
    total_count: int
    advisory_count: int
    categories: list[PostureCategoryWire]


class VulnerabilityCounts(BaseModel):
    total: int
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    tool_credits: list[str] = Field(default_factory=list)


class DashboardPayload(BaseModel):
    """v0.2 dashboard wire shape — see ADR-0032 for the full design rationale."""

    assessment: Assessment | None
    grade: Grade | None
    # Labeled list (ADR-0032 §1.4). The legacy field shape lives on as
    # ``criteria_snapshot`` for any internal caller that still wants the
    # boolean record directly.
    criteria: list[CriterionLabel]
    criteria_snapshot: CriteriaSnapshot
    findings_count_by_priority: dict[str, int]
    posture_pass_count: int
    posture_total_count: int
    posture_checks: list[PostureCheck] = []
    posture: PostureWire | None = None
    tools: list[AssessmentTool] = Field(default_factory=list)
    vulnerabilities: VulnerabilityCounts | None = None
    completion_id: str | None = None


# ------------------------------------------------------------------- helpers
_CATEGORY_DISPLAY: dict[PostureCheckCategory, str] = {
    "repo_configuration": "Repo configuration",
    "code_integrity": "Code integrity",
    "ci_supply_chain": "CI supply chain",
    "collaborator_hygiene": "Collaborator hygiene",
}

# The 10 grading criteria, in the order PRD-0003 v0.2 freezes them — used to
# project ``CriteriaSnapshot`` onto the labeled wire shape. The architect's
# regression test ``test_dashboard_criteria_with_labels`` asserts the labels
# come from the backend, not the frontend.
_CRITERIA_ORDER: list[tuple[str, str, str]] = [
    ("security_md_present", "SECURITY.md present", "security_md_present"),
    ("dependabot_configured", "Dependabot configured", "dependabot_present"),
    ("no_critical_vulns", "No critical vulns", "no_critical_vulns"),
    ("no_high_vulns", "No high vulns", "no_high_vulns"),
    ("branch_protection_enabled", "Branch protection enabled", "branch_protection_enabled"),
    ("no_secrets_detected", "No committed secrets", "no_secrets_detected"),
    ("actions_pinned_to_sha", "CI actions pinned to SHA", "actions_pinned_to_sha"),
    ("no_stale_collaborators", "No stale collaborators", "no_stale_collaborators"),
    ("code_owners_exists", "Code owners file exists", "code_owners_exists"),
    ("secret_scanning_enabled", "Secret scanning enabled", "secret_scanning_enabled"),
]


def _criteria_to_labeled(snapshot: CriteriaSnapshot) -> list[CriterionLabel]:
    snap = snapshot.model_dump()
    return [
        CriterionLabel(key=key, label=label, met=bool(snap.get(field)))
        for key, label, field in _CRITERIA_ORDER
    ]


def _project_posture_state(check: PostureCheck) -> tuple[PostureWireState, str | None]:
    """Apply ADR-0032 §1.2 four-state projection.

    Internal status maps to the wire state; ``advisory`` checks always emit
    ``advisory`` regardless of pass/fail. A ``pr_url`` on the row indicates a
    fix PR has landed, which the dashboard surfaces as ``done`` per the
    architect's read-time projection rule.
    """
    is_advisory = (
        check.check_name in ADVISORY_CHECKS
        or check.status == "advisory"
    )
    if check.pr_url:
        return "done", check.pr_url
    if is_advisory or check.status == "unknown":
        return "advisory", None
    if check.status == "pass":
        return "pass", None
    return "fail", None


def _grade_impact(check_name: str) -> Literal["counts", "advisory"]:
    return "advisory" if check_name in ADVISORY_CHECKS else "counts"


def _build_posture_payload(checks: list[PostureCheck]) -> PostureWire:
    by_category: dict[PostureCheckCategory, list[PostureCheckWire]] = {
        "repo_configuration": [],
        "code_integrity": [],
        "ci_supply_chain": [],
        "collaborator_hygiene": [],
    }
    pass_count = 0
    advisory_count = 0
    for c in checks:
        category = c.category or CHECK_CATEGORY.get(c.check_name, "repo_configuration")
        state, pr_url = _project_posture_state(c)
        wire = PostureCheckWire(
            name=c.check_name,
            display_name=CHECK_DISPLAY_NAME.get(c.check_name, c.check_name),
            category=category,
            state=state,
            grade_impact=_grade_impact(c.check_name),
            detail=(c.detail or {}).get("reason") if isinstance(c.detail, dict) else None,
            pr_url=pr_url,
        )
        by_category.setdefault(category, []).append(wire)
        if state == "advisory":
            advisory_count += 1
        elif state in ("pass", "done"):
            pass_count += 1

    categories: list[PostureCategoryWire] = []
    for cat, items in by_category.items():
        if not items:
            continue
        non_advisory = [it for it in items if it.grade_impact == "counts"]
        progress = CategoryProgress(
            done=sum(1 for it in non_advisory if it.state in ("pass", "done")),
            total=len(non_advisory),
        )
        categories.append(
            PostureCategoryWire(
                name=cat,
                display_name=_CATEGORY_DISPLAY[cat],
                progress=progress,
                checks=items,
            )
        )
    total = sum(1 for c in checks if _grade_impact(c.check_name) == "counts")
    return PostureWire(
        pass_count=pass_count,
        total_count=total,
        advisory_count=advisory_count,
        categories=categories,
    )


_TYPE_TO_SOURCE = {
    "trivy": "dependency",
    "snyk": "dependency",
    "wiz": "dependency",
    "trivy-secret": "secret",
    "gitleaks": "secret",
    "semgrep": "code",
    "codeql": "code",
}


async def _build_vuln_counts(db, started_at_iso: str) -> VulnerabilityCounts:
    findings = await list_findings(
        db,
        source_type="opensec-assessment",
        created_since_iso=started_at_iso,
    )
    by_severity: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    by_source: dict[str, int] = {"dependency": 0, "code": 0, "secret": 0}
    credits: set[str] = set()
    for f in findings:
        if f.normalized_priority and f.normalized_priority in by_severity:
            by_severity[f.normalized_priority] += 1
        source_kind = _TYPE_TO_SOURCE.get((f.source_type or "").lower(), "dependency")
        by_source[source_kind] = by_source.get(source_kind, 0) + 1
        if f.source_type:
            credits.add(f.source_type)
    return VulnerabilityCounts(
        total=len(findings),
        by_severity=by_severity,
        by_source=by_source,
        tool_credits=sorted(credits),
    )


def _synthesize_tools(
    persisted: list[AssessmentTool] | None,
    pass_count: int,
    total_count: int,
    vulns: VulnerabilityCounts | None,
) -> list[AssessmentTool]:
    """Fall back to a synthesized ``tools[]`` when no row was persisted yet.

    The IMPL plan has the engine emit ``tools_json`` directly; until the
    engine rewrite lands the dashboard projects sensible defaults from the
    posture pass count and the vulnerability totals so the UI can render.
    """
    if persisted:
        return persisted
    by_source = (vulns.by_source if vulns else {}) or {}
    dep_count = by_source.get("dependency", 0) + by_source.get("secret", 0)
    code_count = by_source.get("code", 0)
    return [
        AssessmentTool(
            id="trivy",
            label="Trivy",
            version=None,
            icon="bug_report",
            state="done",
            result=AssessmentToolResult(
                kind="findings_count",
                value=dep_count,
                text=f"{dep_count} {'finding' if dep_count == 1 else 'findings'}",
            ),
        ),
        AssessmentTool(
            id="semgrep",
            label="Semgrep",
            version=None,
            icon="code",
            state="done",
            result=AssessmentToolResult(
                kind="findings_count",
                value=code_count,
                text=f"{code_count} {'finding' if code_count == 1 else 'findings'}",
            ),
        ),
        AssessmentTool(
            id="posture",
            label=f"{total_count} posture checks",
            version=None,
            icon="rule",
            state="done",
            result=AssessmentToolResult(
                kind="pass_count", value=pass_count, text=f"{pass_count} pass"
            ),
        ),
    ]


# ------------------------------------------------------------------ endpoint
@router.get("", response_model=DashboardPayload)
async def get_dashboard(db=Depends(get_db)) -> DashboardPayload:
    latest = await get_latest_assessment(db)

    if latest is None:
        empty_snapshot = CriteriaSnapshot()
        return DashboardPayload(
            assessment=None,
            grade=None,
            criteria=_criteria_to_labeled(empty_snapshot),
            criteria_snapshot=empty_snapshot,
            findings_count_by_priority={},
            posture_pass_count=0,
            posture_total_count=0,
            posture_checks=[],
            posture=None,
            tools=[],
            vulnerabilities=None,
            completion_id=None,
        )

    counts = await count_findings_by_priority(
        db,
        source_type="opensec-assessment",
        created_since_iso=latest.started_at.isoformat(),
    )
    pass_count, total_count = await count_posture_pass_total(db, latest.id)
    posture_checks = await list_posture_checks_for_assessment(db, latest.id)
    completion = await get_completion_for_assessment(db, latest.id)
    vulnerabilities = await _build_vuln_counts(db, latest.started_at.isoformat())

    snapshot = latest.criteria_snapshot or CriteriaSnapshot()
    completion_id = (
        completion.id
        if completion is not None and latest.grade == "A" and snapshot.all_met()
        else None
    )

    posture_wire = _build_posture_payload(posture_checks)
    tools = _synthesize_tools(latest.tools, pass_count, total_count, vulnerabilities)

    return DashboardPayload(
        assessment=latest,
        grade=latest.grade,
        criteria=_criteria_to_labeled(snapshot),
        criteria_snapshot=snapshot,
        findings_count_by_priority=counts,
        posture_pass_count=pass_count,
        posture_total_count=total_count,
        posture_checks=posture_checks,
        posture=posture_wire,
        tools=tools,
        vulnerabilities=vulnerabilities,
        completion_id=completion_id,
    )
