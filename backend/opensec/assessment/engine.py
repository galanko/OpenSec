"""Assessment orchestrator (PRD-0003 v0.2 / IMPL-0003-p2 Phase 1).

`run_assessment` is the canonical entry point for a full repo scan. It clones
the target repo, runs Trivy + Semgrep via the :class:`ScannerRunner` (ADR-0028
subprocess-only execution), runs the 15 posture checks (PRD-0003 rev. 2), and
returns an :class:`AssessmentResult` with the full ``tools[]`` payload from
ADR-0032 already populated.

The function is pure-ish — DB persistence happens in ``api/_background.py``;
this module only emits in-memory results plus optional progress callbacks
(``on_step`` for the six-stage timeline, ``on_tool`` for the three-pill
ToolPillBar). Trivy failure is fatal; Semgrep failure is graceful (the tool
becomes ``skipped`` and the assessment continues without it).

The legacy lockfile parsers and OSV/GHSA HTTP clients used by PRD-0002's engine
are gone — Trivy subsumes both responsibilities. See IMPL-0003-p2 Phase 1 for
the deletion list.
"""

from __future__ import annotations

import contextlib
import logging
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from opensec.assessment.clone import shallow_clone
from opensec.assessment.posture import RepoCoords, run_all_posture_checks
from opensec.models.assessment import (
    AssessmentResult,
    AssessmentTool,
    AssessmentToolResult,
    CriteriaSnapshot,
)
from opensec.models.finding import FindingCreate

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from opensec.assessment.posture import GithubAPI
    from opensec.assessment.scanners.models import (
        SemgrepResult,
        TrivyResult,
    )
    from opensec.assessment.scanners.runner import ScannerRunner
    from opensec.models.assessment import Grade
    from opensec.models.posture_check import PostureCheckName, PostureCheckStatus

logger = logging.getLogger(__name__)


#: Hard timeout budget for each scanner subprocess. Trivy ships a vuln+secret
#: scan on a mid-size repo in ~30s on cold cache; Semgrep is similar.
_TRIVY_TIMEOUT_S: float = 120.0
_SEMGREP_TIMEOUT_S: float = 120.0
_CLONE_TIMEOUT_S: float = 60.0


# --------------------------------------------------------------------- cloning


class RepoCloner:
    """Async context manager around :func:`shallow_clone` (ADR-0024).

    Production usage::

        async with cloner.clone("https://github.com/owner/repo") as repo_path:
            ...

    The temp directory is removed on exit regardless of success.
    """

    def __init__(
        self,
        *,
        token_provider: Callable[[], Awaitable[str | None]] | None = None,
        tmp_root: Path | None = None,
        timeout_s: float = _CLONE_TIMEOUT_S,
    ) -> None:
        self._token_provider = token_provider
        self._tmp_root = tmp_root
        self._timeout_s = timeout_s

    @contextlib.asynccontextmanager
    async def clone(
        self, repo_url: str, *, branch: str = "main"
    ) -> AsyncIterator[Path]:
        # ``branch`` is accepted for API symmetry; ``shallow_clone`` already
        # uses ``--single-branch`` and resolves the default branch on its own.
        del branch
        token: str | None = None
        if self._token_provider is not None:
            token = await self._token_provider()

        if self._tmp_root is not None:
            self._tmp_root.mkdir(parents=True, exist_ok=True)

        tmp_root_str = str(self._tmp_root) if self._tmp_root else None
        tmp = Path(tempfile.mkdtemp(prefix="opensec-clone-", dir=tmp_root_str))
        try:
            target = tmp / "repo"
            target.mkdir()
            await shallow_clone(
                repo_url, target=target, token=token, timeout_s=self._timeout_s
            )
            yield target
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------- engine


async def run_assessment(
    repo_url: str,
    *,
    gh_client: GithubAPI,
    runner: ScannerRunner,
    cloner: RepoCloner,
    assessment_id: str,
    on_step: Callable[[str], Awaitable[None]] | None = None,
    on_tool: Callable[[AssessmentTool], Awaitable[None]] | None = None,
    branch: str = "main",
) -> AssessmentResult:
    """Clone -> Trivy -> Semgrep -> posture -> assemble result.

    ``assessment_id`` is supplied by the caller (the API layer creates the DB
    row before scheduling the run). The engine never generates its own.

    ``on_step`` receives one of the six stage keys per IMPL-0003-p2 Phase 1:
    ``detect``, ``trivy_vuln``, ``trivy_secret``, ``semgrep``, ``posture``,
    ``descriptions``. The route layer maps this onto a steps[] timeline.

    ``on_tool`` receives an updated :class:`AssessmentTool` whenever a pill's
    state transitions. The initial broadcast emits all three tools as
    ``pending`` so the UI can render the bar from t=0.

    Trivy failure is fatal: the engine raises and the orchestrator marks the
    assessment ``failed``. Semgrep failure is graceful: the corresponding tool
    becomes ``skipped`` and the assessment continues. Per-check posture
    exceptions surface as ``status='unknown'`` from the posture orchestrator;
    they do not abort the run.
    """
    coords = _coords_from_repo_url(repo_url, branch=branch)

    # Initial tools[] broadcast — three pending pills.
    tools: dict[str, AssessmentTool] = {
        "trivy": AssessmentTool(
            id="trivy", label="Trivy", icon="bug_report", state="pending"
        ),
        "semgrep": AssessmentTool(
            id="semgrep", label="Semgrep", icon="code", state="pending"
        ),
        "posture": AssessmentTool(
            id="posture", label="15 posture checks", icon="rule", state="pending"
        ),
    }
    for tool in tools.values():
        await _emit_tool(on_tool, tool)

    # 1. Clone (the "detect" stage covers clone + project-type sniffing).
    await _emit_step(on_step, "detect")
    async with cloner.clone(repo_url, branch=branch) as repo_path:

        # 2. Trivy (vuln + secret in one invocation; UI shows two stage rows
        #    but the tool transitions once).
        tools["trivy"] = tools["trivy"].model_copy(update={"state": "active"})
        await _emit_tool(on_tool, tools["trivy"])
        await _emit_step(on_step, "trivy_vuln")
        try:
            trivy_result = await runner.run_trivy(
                repo_path, timeout=_TRIVY_TIMEOUT_S
            )
        except Exception:
            tools["trivy"] = tools["trivy"].model_copy(update={"state": "skipped"})
            await _emit_tool(on_tool, tools["trivy"])
            logger.exception("trivy failed; assessment is fatally failing")
            raise

        await _emit_step(on_step, "trivy_secret")

        # 3. Semgrep (graceful skip).
        tools["semgrep"] = tools["semgrep"].model_copy(update={"state": "active"})
        await _emit_tool(on_tool, tools["semgrep"])
        await _emit_step(on_step, "semgrep")
        semgrep_result: SemgrepResult | None = None
        semgrep_ran = False
        try:
            semgrep_result = await runner.run_semgrep(
                repo_path, timeout=_SEMGREP_TIMEOUT_S
            )
            semgrep_ran = True
        except Exception:
            logger.warning("semgrep failed; continuing without it", exc_info=True)
            tools["semgrep"] = tools["semgrep"].model_copy(
                update={"state": "skipped"}
            )
            await _emit_tool(on_tool, tools["semgrep"])

        # 4. Posture (15 checks; per-check `unknown` is not a failure).
        tools["posture"] = tools["posture"].model_copy(update={"state": "active"})
        await _emit_tool(on_tool, tools["posture"])
        await _emit_step(on_step, "posture")
        posture_results = await run_all_posture_checks(
            repo_path,
            gh_client=gh_client,
            coords=coords,
            assessment_id=assessment_id,
        )

    # 5. Finalize tool results.
    trivy_count = len(trivy_result.vulnerabilities) + len(trivy_result.secrets)
    tools["trivy"] = tools["trivy"].model_copy(
        update={
            "state": "done",
            "version": trivy_result.version or None,
            "label": _label_for("Trivy", trivy_result.version),
            "result": AssessmentToolResult(
                kind="findings_count",
                value=trivy_count,
                text=_pluralize(trivy_count, "finding"),
            ),
        }
    )
    await _emit_tool(on_tool, tools["trivy"])

    if semgrep_ran and semgrep_result is not None:
        sg_count = len(semgrep_result.findings)
        tools["semgrep"] = tools["semgrep"].model_copy(
            update={
                "state": "done",
                "version": semgrep_result.version or None,
                "label": _label_for("Semgrep", semgrep_result.version),
                "result": AssessmentToolResult(
                    kind="findings_count",
                    value=sg_count,
                    text=_pluralize(sg_count, "finding"),
                ),
            }
        )
        await _emit_tool(on_tool, tools["semgrep"])

    posture_pass = sum(1 for pc in posture_results if pc.status == "pass")
    tools["posture"] = tools["posture"].model_copy(
        update={
            "state": "done",
            "result": AssessmentToolResult(
                kind="pass_count",
                value=posture_pass,
                text=f"{posture_pass} pass",
            ),
        }
    )
    await _emit_tool(on_tool, tools["posture"])

    # 6. Snapshot + grade.
    await _emit_step(on_step, "descriptions")
    posture_statuses: dict[PostureCheckName, PostureCheckStatus] = {
        pc.check_name: pc.status for pc in posture_results
    }
    findings_dicts = _trivy_findings_to_dicts(trivy_result)
    snapshot = _build_snapshot(findings_dicts, posture_statuses)
    grade = derive_grade(snapshot, findings_dicts, posture_statuses)

    return AssessmentResult(
        assessment_id=assessment_id,
        repo_url=repo_url,
        grade=grade,
        criteria_snapshot=snapshot,
        findings=findings_dicts,
        posture_checks=[
            {
                "check_name": pc.check_name,
                "status": pc.status,
                "detail": pc.detail,
            }
            for pc in posture_results
        ],
        tools=list(tools.values()),
    )


# --------------------------------------------------------------------- helpers


async def _emit_step(
    cb: Callable[[str], Awaitable[None]] | None, step: str
) -> None:
    if cb is None:
        return
    try:
        await cb(step)
    except Exception:  # noqa: BLE001 — never let a UI callback break the run
        logger.debug("on_step callback raised for step=%s", step, exc_info=True)


async def _emit_tool(
    cb: Callable[[AssessmentTool], Awaitable[None]] | None,
    tool: AssessmentTool,
) -> None:
    if cb is None:
        return
    try:
        await cb(tool)
    except Exception:  # noqa: BLE001
        logger.debug("on_tool callback raised for tool=%s", tool.id, exc_info=True)


def _label_for(name: str, version: str | None) -> str:
    if version and version != "unknown":
        return f"{name} {version}"
    return name


def _pluralize(n: int, noun: str) -> str:
    return f"{n} {noun}{'' if n == 1 else 's'}"


# Trivy → FindingCreate-shaped dicts. Phase 1 keeps the legacy ``finding`` table
# shape; Phase 2 swaps this for the deterministic mappers in ``to_findings.py``.
def _trivy_findings_to_dicts(result: TrivyResult) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for v in result.vulnerabilities:
        findings.append(
            FindingCreate(
                source_type="trivy",
                source_id=f"{v.pkg_name}@{v.installed_version}:{v.vuln_id}",
                title=v.title or v.vuln_id,
                description=v.description,
                raw_severity=v.severity,
                normalized_priority=_priority_from_severity(v.severity),
                asset_label=f"{v.pkg_name}@{v.installed_version}",
                raw_payload={
                    "vuln_id": v.vuln_id,
                    "package": v.pkg_name,
                    "version": v.installed_version,
                    "fixed_version": v.fixed_version,
                    "primary_url": v.primary_url,
                },
            ).model_dump()
        )
    for s in result.secrets:
        findings.append(
            FindingCreate(
                source_type="trivy-secret",
                source_id=f"{s.path}:{s.start_line}:{s.rule_id}",
                title=s.title or s.rule_id,
                description=s.match,
                raw_severity=s.severity,
                normalized_priority=_priority_from_severity(s.severity),
                asset_label=s.path,
                raw_payload={
                    "rule_id": s.rule_id,
                    "category": s.category,
                    "path": s.path,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                },
            ).model_dump()
        )
    return findings


_PRIORITY_BY_SEVERITY: dict[str, str] = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MODERATE": "medium",
    "MEDIUM": "medium",
    "LOW": "low",
    "WARNING": "medium",
    "ERROR": "high",
    "INFO": "low",
}


def _priority_from_severity(raw_severity: str | None) -> str | None:
    if not isinstance(raw_severity, str):
        return None
    return _PRIORITY_BY_SEVERITY.get(raw_severity.upper())


def derive_grade(
    criteria: CriteriaSnapshot,
    findings: list[dict[str, Any]] | None = None,
    posture_statuses: dict[PostureCheckName, PostureCheckStatus] | None = None,
) -> Grade:
    """Ten-criteria grading per PRD-0003 v0.2 / ADR-0032.

    A=10, B=8-9, C=6-7, D=4-5, F=0-3. The optional ``findings`` and
    ``posture_statuses`` arguments allow legacy callers that synthesize a
    snapshot without the v0.2 fields to grade correctly — we re-derive the
    relevant booleans before counting.
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
    severities = {_severity_of(f) for f in findings}
    has_unknown = "UNKNOWN" in severities
    no_high = (
        criteria.no_high_vulns
        if criteria.no_high_vulns
        else "HIGH" not in severities and not has_unknown
    )
    return criteria.model_copy(
        update={
            "no_critical_vulns": criteria.no_critical_vulns
            or ("CRITICAL" not in severities and not has_unknown),
            "no_high_vulns": no_high,
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


def _build_snapshot(
    findings: list[dict[str, Any]],
    posture_statuses: dict[PostureCheckName, PostureCheckStatus],
) -> CriteriaSnapshot:
    severities = {_severity_of(f) for f in findings}
    has_unknown = "UNKNOWN" in severities
    passing = sum(1 for s in posture_statuses.values() if s == "pass")
    return CriteriaSnapshot(
        no_critical_vulns="CRITICAL" not in severities and not has_unknown,
        no_high_vulns=(
            "HIGH" not in severities
            and "CRITICAL" not in severities
            and not has_unknown
        ),
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
    """Parse `owner/repo` out of an HTTPS or SSH URL.

    Raises ``ValueError`` on anything we can't confidently parse — the GitHub
    API client would otherwise 404 silently and every protection-dependent
    posture check would report ``unknown``.
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


__all__ = [
    "RepoCloner",
    "_coords_from_repo_url",
    "derive_grade",
    "run_assessment",
]
