"""Assessment orchestrator (IMPL-0002 B6, ADR-0025 §1).

Composes the three pure layers — parsers, advisory lookups, and posture
checks — into a single `AssessmentResult`. No DB writes: Session B owns
persistence. No LLM: Session C owns plain-language normalisation.

Public entry points:
- `run_assessment_on_path(repo_path, ...)` — what Session A tests exercise.
- `run_assessment(repo_url)` — clones then delegates. Left as `NotImplementedError`
  until `RepoCloner` lands (ADR-0024). Session B mocks `run_assessment` at the
  route boundary per EXEC-0002, so this is safe for today.
- `derive_grade(...)` — pure function, reusable by downstream read paths.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import urlparse

from opensec.assessment.osv_client import lookup_with_fallback
from opensec.assessment.parsers import detect_lockfiles
from opensec.assessment.posture import RepoCoords, run_all_posture_checks
from opensec.models.assessment import AssessmentResult, CriteriaSnapshot
from opensec.models.finding import FindingCreate

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.assessment.osv_client import Advisory, OsvClient
    from opensec.assessment.parsers.base import ParsedDependency
    from opensec.models.assessment import Grade


class _GithubAPI(Protocol):
    async def get_branch_protection(
        self, owner: str, repo: str, branch: str
    ) -> Any: ...

    async def list_recent_commits(
        self, owner: str, repo: str, branch: str, *, limit: int = 20
    ) -> Any: ...


class _AdvisoryLookup(Protocol):
    async def lookup(self, dep: ParsedDependency) -> list[Advisory]: ...


async def run_assessment(repo_url: str) -> AssessmentResult:
    """Top-level entry — clones and delegates.

    TODO(ADR-0024): wire `RepoCloner` when it lands in its own PR. For now
    Session A unit tests target `run_assessment_on_path` directly and
    Session B mocks `run_assessment` at the route boundary.
    """
    raise NotImplementedError(
        "run_assessment requires RepoCloner (ADR-0024). "
        "Call run_assessment_on_path directly in tests."
    )


async def run_assessment_on_path(
    repo_path: Path,
    *,
    repo_url: str,
    gh_client: _GithubAPI,
    osv: OsvClient | _AdvisoryLookup,
    ghsa: _AdvisoryLookup | None = None,
    branch: str = "main",
) -> AssessmentResult:
    assessment_id = str(uuid.uuid4())
    coords = _coords_from_repo_url(repo_url, branch=branch)

    # 1. Parse every detected lockfile, dedupe.
    deps = _collect_dependencies(repo_path)

    # 2. Advisory lookups (OSV, degrade to GHSA, degrade to unable-to-verify).
    findings = await _build_findings(deps, osv=osv, ghsa=ghsa)

    # 3. Posture checks — fixed 7.
    posture_checks = await run_all_posture_checks(
        repo_path, gh_client=gh_client, coords=coords, assessment_id=assessment_id
    )
    posture_statuses = {pc.check_name: pc.status for pc in posture_checks}

    # 4. Derive the criteria snapshot and grade.
    snapshot = _build_snapshot(findings, posture_statuses)
    grade = derive_grade(snapshot, findings, posture_statuses)

    return AssessmentResult(
        assessment_id=assessment_id,
        repo_url=repo_url,
        grade=grade,
        criteria_snapshot=snapshot,
        findings=findings,
        posture_checks=[pc.model_dump() for pc in posture_checks],
    )


def derive_grade(
    criteria: CriteriaSnapshot,
    findings: list[dict[str, Any]],
    posture_statuses: dict[str, str] | None = None,
) -> Grade:
    """Five-criteria derivation per ADR-0025 §2.

    Criteria:
        1. Zero open critical vulnerability findings
        2. Zero open high vulnerability findings
        3. Branch protection enabled on default branch
        4. No secrets detected
        5. SECURITY.md exists

    Count met, map to grade: 5->A, 4->B, 3->C, 2->D, else F.
    """
    posture_statuses = posture_statuses or {}
    severities = [_severity_of(f) for f in findings]

    met = 0
    if "CRITICAL" not in severities:
        met += 1
    if "HIGH" not in severities:
        met += 1
    if posture_statuses.get("branch_protection") == "pass":
        met += 1
    if posture_statuses.get("no_secrets_in_code") == "pass":
        met += 1
    if criteria.security_md_present:
        met += 1

    if met == 5:
        return "A"
    if met == 4:
        return "B"
    if met == 3:
        return "C"
    if met == 2:
        return "D"
    return "F"


# ---------------------------------------------------------------------------
# internal helpers
# ---------------------------------------------------------------------------


def _collect_dependencies(repo_path: Path) -> list[ParsedDependency]:
    seen: set[tuple[str, str, str]] = set()
    deps: list[ParsedDependency] = []
    for _ecosystem, file_path, parser in detect_lockfiles(repo_path):
        try:
            parsed = parser(file_path)
        except Exception:  # noqa: BLE001 — one malformed lockfile shouldn't kill the run
            continue
        for dep in parsed:
            key = (dep.ecosystem, dep.name, dep.version)
            if key in seen:
                continue
            seen.add(key)
            deps.append(dep)
    return deps


async def _build_findings(
    deps: list[ParsedDependency],
    *,
    osv: OsvClient | _AdvisoryLookup,
    ghsa: _AdvisoryLookup | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for dep in deps:
        result = await lookup_with_fallback(dep, osv=osv, ghsa=ghsa)  # type: ignore[arg-type]
        if result.unable_to_verify or not result.advisories:
            continue
        for advisory in result.advisories:
            findings.append(_finding_from_advisory(advisory, dep))
    return findings


def _finding_from_advisory(
    advisory: Advisory, dep: ParsedDependency
) -> dict[str, Any]:
    title = advisory.summary or f"{dep.name}@{dep.version} vulnerable"
    return FindingCreate(
        source_type="osv",
        source_id=advisory.id,
        title=title,
        description=advisory.summary or None,
        raw_severity=advisory.severity,
        asset_label=f"{dep.name}@{dep.version}",
        raw_payload={
            "advisory_id": advisory.id,
            "ecosystem": dep.ecosystem,
            "package": dep.name,
            "version": dep.version,
            "fixed_version": advisory.fixed_version,
            "source": advisory.raw,
        },
    ).model_dump()


def _build_snapshot(
    findings: list[dict[str, Any]], posture_statuses: dict[str, str]
) -> CriteriaSnapshot:
    severities = [_severity_of(f) for f in findings]
    passing = sum(1 for s in posture_statuses.values() if s == "pass")
    return CriteriaSnapshot(
        no_critical_vulns="CRITICAL" not in severities,
        posture_checks_passing=passing,
        posture_checks_total=len(posture_statuses) or 7,
        security_md_present=posture_statuses.get("security_md") == "pass",
        dependabot_present=posture_statuses.get("dependabot_config") == "pass",
    )


def _severity_of(finding: dict[str, Any]) -> str:
    raw = finding.get("raw_severity")
    if isinstance(raw, str):
        return raw.upper()
    return "UNKNOWN"


def _coords_from_repo_url(repo_url: str, *, branch: str) -> RepoCoords:
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    parts = path.split("/", 1)
    if len(parts) == 2:
        owner, repo = parts
    else:
        owner, repo = ("", path or "")
    return RepoCoords(owner=owner, repo=repo, branch=branch)
