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
) -> AssessmentResult:
    assessment_id = str(uuid.uuid4())
    coords = _coords_from_repo_url(repo_url, branch=branch)

    lockfiles = detect_lockfiles(repo_path)
    deps = _collect_dependencies(lockfiles)
    findings = await _build_findings(deps, osv=osv, ghsa=ghsa)

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
    posture_statuses: dict[PostureCheckName, PostureCheckStatus] | None = None,
) -> Grade:
    """Five-criteria derivation per ADR-0025 §2.

    Met criteria: no criticals, no highs, branch_protection pass,
    no_secrets_in_code pass, SECURITY.md present. Count -> A..F.

    Policy: an advisory with UNKNOWN severity fails criterion 1 and 2 —
    we treat "could be critical" as "is critical" for grading. Operators
    see the grade drop and investigate rather than silently benefiting
    from missing severity metadata.
    """
    posture_statuses = posture_statuses or {}
    severities = {_severity_of(f) for f in findings}
    has_unknown = "UNKNOWN" in severities

    met = sum(
        [
            "CRITICAL" not in severities and not has_unknown,
            "HIGH" not in severities and not has_unknown,
            posture_statuses.get("branch_protection") == "pass",
            posture_statuses.get("no_secrets_in_code") == "pass",
            criteria.security_md_present,
        ]
    )
    return {5: "A", 4: "B", 3: "C", 2: "D"}.get(met, "F")


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


def _finding_from_advisory(advisory: Advisory, dep: ParsedDependency) -> dict[str, Any]:
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
    findings: list[dict[str, Any]],
    posture_statuses: dict[PostureCheckName, PostureCheckStatus],
) -> CriteriaSnapshot:
    severities = {_severity_of(f) for f in findings}
    passing = sum(1 for s in posture_statuses.values() if s == "pass")
    return CriteriaSnapshot(
        no_critical_vulns="CRITICAL" not in severities,
        posture_checks_passing=passing,
        posture_checks_total=len(posture_statuses),
        security_md_present=posture_statuses.get("security_md") == "pass",
        dependabot_present=posture_statuses.get("dependabot_config") == "pass",
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
