"""Assessment orchestrator.

Composes parsers, advisory lookups, and posture checks into a single
`AssessmentResult`. Pure — no DB writes, no LLM, no outbound clone.

Entry points:
- `run_assessment_on_path` — what unit tests exercise.
- `run_assessment` — stub pending `RepoCloner` (ADR-0024).
- `derive_grade` — pure helper; the read path recomputes on every request.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from opensec.assessment.osv_client import lookup_with_fallback
from opensec.assessment.parsers import detect_lockfiles
from opensec.assessment.posture import RepoCoords, run_all_posture_checks
from opensec.models.assessment import AssessmentResult, CriteriaSnapshot
from opensec.models.finding import FindingCreate

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from opensec.assessment.osv_client import Advisory, AdvisoryLookup
    from opensec.assessment.parsers.base import ParsedDependency
    from opensec.assessment.posture import GithubAPI
    from opensec.models.assessment import Grade
    from opensec.models.posture_check import PostureCheckName, PostureCheckStatus

logger = logging.getLogger(__name__)

# Cap on concurrent advisory lookups. OSV tolerates this easily and
# `httpx.AsyncClient` reuses its connection pool. Without this, ~1000 deps
# serialized at 50 ms each blows the ADR-0025 ~10s assessment budget.
_LOOKUP_CONCURRENCY = 10


async def run_assessment(repo_url: str) -> AssessmentResult:
    raise NotImplementedError(
        "run_assessment requires RepoCloner (ADR-0024); "
        "use run_assessment_on_path until it lands."
    )


async def run_assessment_on_path(
    repo_path: Path,
    *,
    repo_url: str,
    gh_client: GithubAPI,
    osv: AdvisoryLookup,
    ghsa: AdvisoryLookup | None = None,
    branch: str = "main",
    on_step: Callable[[str], Awaitable[None]] | None = None,
) -> AssessmentResult:
    """Run a full assessment on a checked-out repo.

    ``on_step`` is an optional async callback invoked at the start of each
    visible phase — ``parsing_lockfiles``, ``looking_up_cves``,
    ``checking_posture``, ``grading`` — so the API layer can expose progress
    to the status endpoint. No-op when ``None``.
    """
    assessment_id = str(uuid.uuid4())
    coords = _coords_from_repo_url(repo_url, branch=branch)

    async def _emit(step: str) -> None:
        if on_step is not None:
            try:
                await on_step(step)
            except Exception:  # noqa: BLE001
                logger.debug("on_step callback raised for step=%s", step, exc_info=True)

    await _emit("parsing_lockfiles")
    lockfiles = detect_lockfiles(repo_path)
    deps = _collect_dependencies(lockfiles)

    await _emit("looking_up_cves")
    findings = await _build_findings(deps, osv=osv, ghsa=ghsa)

    await _emit("checking_posture")
    posture_checks = await run_all_posture_checks(
        repo_path,
        gh_client=gh_client,
        coords=coords,
        assessment_id=assessment_id,
        pre_detected_lockfiles=lockfiles,
    )
    posture_statuses: dict[PostureCheckName, PostureCheckStatus] = {
        pc.check_name: pc.status for pc in posture_checks
    }

    await _emit("grading")
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
    findings: list[dict[str, Any]] | None = None,
    posture_statuses: dict[PostureCheckName, PostureCheckStatus] | None = None,
) -> Grade:
    """Ten-criteria derivation per PRD-0003 v0.2 / ADR-0032.

    The criteria the dashboard renders as a labeled list:

    1. SECURITY.md present
    2. Dependabot/Renovate configured
    3. No critical vulns
    4. No high-severity vulns                       (NEW v0.2)
    5. Branch protection enabled                    (NEW v0.2)
    6. No committed secrets                         (NEW v0.2)
    7. CI actions pinned to SHA                     (NEW v0.2)
    8. No stale collaborators                       (NEW v0.2)
    9. Code owners file exists                      (NEW v0.2)
    10. Secret scanning enabled                     (NEW v0.2)

    Scale: A=10, B=8-9, C=6-7, D=4-5, F=0-3.

    The optional ``findings`` and ``posture_statuses`` arguments are accepted
    for backward compatibility — when callers pass them we recompute the
    boolean fields on the snapshot directly so legacy tests that synthesize a
    snapshot without the new fields still grade correctly.
    """
    snapshot = _enrich_snapshot(criteria, findings or [], posture_statuses or {})
    met = snapshot.met_count()
    if met == 10:
        return "A"
    if met >= 8:
        return "B"
    if met >= 6:
        return "C"
    if met >= 4:
        return "D"
    return "F"


def _enrich_snapshot(
    criteria: CriteriaSnapshot,
    findings: list[dict[str, Any]],
    posture_statuses: dict[PostureCheckName, PostureCheckStatus],
) -> CriteriaSnapshot:
    """Backfill v0.2 booleans onto a legacy snapshot before grading.

    Older code paths construct a snapshot with the original five fields and
    rely on ``derive_grade`` to score it. The new criteria are derived from
    the same posture-status map and finding severities; this keeps the
    grader's contract one-shot rather than forcing every call site to
    repopulate every field.
    """
    severities = {_severity_of(f) for f in findings}
    has_unknown = "UNKNOWN" in severities
    no_high_vulns = (
        criteria.no_high_vulns
        if criteria.no_high_vulns
        else "HIGH" not in severities and not has_unknown
    )
    return criteria.model_copy(
        update={
            "no_critical_vulns": criteria.no_critical_vulns
            or ("CRITICAL" not in severities and not has_unknown),
            "no_high_vulns": no_high_vulns,
            "branch_protection_enabled": criteria.branch_protection_enabled
            or posture_statuses.get("branch_protection") == "pass",
            "no_secrets_detected": criteria.no_secrets_detected
            or posture_statuses.get("no_secrets_in_code") == "pass",
            "actions_pinned_to_sha": criteria.actions_pinned_to_sha
            or posture_statuses.get("actions_pinned_to_sha") == "pass",
            "no_stale_collaborators": criteria.no_stale_collaborators
            or posture_statuses.get("stale_collaborators") == "pass",
            "code_owners_exists": criteria.code_owners_exists
            or posture_statuses.get("code_owners_exists") == "pass",
            "secret_scanning_enabled": criteria.secret_scanning_enabled
            or posture_statuses.get("secret_scanning_enabled") == "pass",
        }
    )


def _collect_dependencies(
    lockfiles: list[tuple[str, Path, Any]],
) -> list[ParsedDependency]:
    seen: set[tuple[str, str, str]] = set()
    deps: list[ParsedDependency] = []
    for _ecosystem, file_path, parser in lockfiles:
        try:
            parsed = parser(file_path)
        except Exception as exc:  # noqa: BLE001 — one malformed lockfile shouldn't kill the run
            logger.warning(
                "assessment: skipped malformed lockfile %s: %s",
                file_path,
                exc,
            )
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
    osv: AdvisoryLookup,
    ghsa: AdvisoryLookup | None,
) -> list[dict[str, Any]]:
    if not deps:
        return []
    semaphore = asyncio.Semaphore(_LOOKUP_CONCURRENCY)

    async def _one(dep: ParsedDependency) -> list[dict[str, Any]]:
        async with semaphore:
            result = await lookup_with_fallback(dep, osv=osv, ghsa=ghsa)
        if result.unable_to_verify or not result.advisories:
            return []
        return [_finding_from_advisory(a, dep) for a in result.advisories]

    per_dep = await asyncio.gather(*(_one(d) for d in deps))
    return [finding for batch in per_dep for finding in batch]


# Deterministic severity -> normalized_priority mapping. The LLM normalizer
# is bypassed for OSV/GHSA findings because the severity is already reliable
# upstream; leaving normalized_priority NULL hides findings from the
# dashboard (it GROUPs BY normalized_priority WHERE IS NOT NULL).
_PRIORITY_BY_SEVERITY: dict[str, str] = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "medium",
    "MEDIUM": "medium",
    "LOW": "low",
}


def _priority_from_severity(raw_severity: str | None) -> str | None:
    if not isinstance(raw_severity, str):
        return None
    return _PRIORITY_BY_SEVERITY.get(raw_severity.upper())


def _finding_from_advisory(advisory: Advisory, dep: ParsedDependency) -> dict[str, Any]:
    title = advisory.summary or f"{dep.name}@{dep.version} vulnerable"
    return FindingCreate(
        source_type="osv",
        source_id=advisory.id,
        title=title,
        description=advisory.summary or None,
        raw_severity=advisory.severity,
        normalized_priority=_priority_from_severity(advisory.severity),
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
    findings: list[dict[str, Any]],
    posture_statuses: dict[PostureCheckName, PostureCheckStatus],
) -> CriteriaSnapshot:
    severities = {_severity_of(f) for f in findings}
    passing = sum(1 for s in posture_statuses.values() if s == "pass")
    return CriteriaSnapshot(
        no_critical_vulns="CRITICAL" not in severities,
        no_high_vulns="HIGH" not in severities and "CRITICAL" not in severities,
        posture_checks_passing=passing,
        posture_checks_total=len(posture_statuses),
        security_md_present=posture_statuses.get("security_md") == "pass",
        dependabot_present=posture_statuses.get("dependabot_config") == "pass",
        branch_protection_enabled=posture_statuses.get("branch_protection") == "pass",
        no_secrets_detected=posture_statuses.get("no_secrets_in_code") == "pass",
        actions_pinned_to_sha=posture_statuses.get("actions_pinned_to_sha") == "pass",
        no_stale_collaborators=posture_statuses.get("stale_collaborators") == "pass",
        code_owners_exists=posture_statuses.get("code_owners_exists") == "pass",
        secret_scanning_enabled=posture_statuses.get("secret_scanning_enabled") == "pass",
    )


def _severity_of(finding: dict[str, Any]) -> str:
    raw = finding.get("raw_severity")
    return raw.upper() if isinstance(raw, str) else "UNKNOWN"


def _coords_from_repo_url(repo_url: str, *, branch: str) -> RepoCoords:
    """Parse `owner/repo` out of the URL we're assessing.

    Accepts `https://host/owner/repo[.git][/]` and `git@host:owner/repo[.git]`
    (SSH). Raises `ValueError` on anything we can't confidently parse — the
    GitHub API client would otherwise 404 silently and every
    protection-dependent check would report `"unknown"`.
    """
    if repo_url.startswith("git@") and ":" in repo_url:
        path = repo_url.split(":", 1)[1]
    else:
        parsed = urlparse(repo_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"cannot parse owner/repo from repo_url: {repo_url!r}")
        path = parsed.path

    path = path.strip("/").removesuffix(".git")
    owner, _, repo = path.partition("/")
    if not owner or not repo:
        raise ValueError(f"cannot parse owner/repo from repo_url: {repo_url!r}")
    return RepoCoords(owner=owner, repo=repo, branch=branch)
