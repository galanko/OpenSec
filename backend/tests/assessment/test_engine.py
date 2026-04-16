"""End-to-end orchestrator tests (IMPL-0002 B6).

Exercises `run_assessment_on_path` against a synthesised repo with planted
vulns, planted posture issues, and injected mocks for the HTTP clients.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from opensec.assessment.engine import derive_grade, run_assessment_on_path
from opensec.assessment.osv_client import Advisory
from opensec.assessment.posture.github_client import UnableToVerify
from opensec.models.assessment import CriteriaSnapshot

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _osv_braces_advisory() -> Advisory:
    payload = json.loads((FIXTURES / "osv" / "braces_3_0_2.json").read_text())
    v = payload["vulns"][0]
    return Advisory(
        id=v["id"],
        summary=v["summary"],
        severity=v["database_specific"]["severity"],
        fixed_version="3.0.3",
        raw=v,
    )


@pytest.fixture
def planted_repo(tmp_path: Path) -> Path:
    """Repo seeded with one vulnerable lockfile + one AWS key + no SECURITY.md."""
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "name": "demo",
                "lockfileVersion": 3,
                "packages": {
                    "": {"name": "demo", "version": "1.0.0"},
                    "node_modules/braces": {"version": "3.0.2"},
                },
            }
        )
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "config.js").write_text(
        "export const AWS = 'AKIAIOSFODNN7EXAMPLE';\n"
    )
    return tmp_path


@pytest.mark.asyncio
async def test_run_assessment_on_path_produces_expected_findings_and_posture_checks(
    planted_repo: Path,
) -> None:
    gh = AsyncMock()
    gh.get_branch_protection.return_value = UnableToVerify(reason="http_403")
    gh.list_recent_commits.return_value = []

    osv = AsyncMock()
    osv.lookup.return_value = [_osv_braces_advisory()]

    result = await run_assessment_on_path(
        planted_repo,
        repo_url="https://github.com/acme/demo",
        gh_client=gh,
        osv=osv,
    )

    # Top-level shape.
    assert result.repo_url == "https://github.com/acme/demo"
    assert result.assessment_id  # non-empty uuid
    assert result.grade in {"A", "B", "C", "D", "F"}

    # Findings: braces advisory surfaced as a FindingCreate-compatible dict.
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding["source_type"] == "osv"
    assert finding["source_id"] == "GHSA-grv7-fg5c-xmjg"
    assert finding["asset_label"] == "braces@3.0.2"
    assert finding["raw_severity"] == "HIGH"
    assert finding["raw_payload"]["fixed_version"] == "3.0.3"
    assert "braces" in finding["title"].lower()

    # Posture checks: exactly 7, with expected statuses.
    statuses = {pc["check_name"]: pc["status"] for pc in result.posture_checks}
    assert len(statuses) == 7
    assert statuses["no_secrets_in_code"] == "fail"
    assert statuses["security_md"] == "fail"
    assert statuses["dependabot_config"] == "fail"
    assert statuses["lockfile_present"] == "pass"
    assert statuses["branch_protection"] == "unknown"
    assert statuses["no_force_pushes"] == "unknown"

    # Criteria snapshot.
    snap = result.criteria_snapshot
    assert snap is not None
    assert snap.no_critical_vulns is True  # HIGH, not CRITICAL
    assert snap.security_md_present is False
    assert snap.dependabot_present is False
    assert snap.posture_checks_total == 7
    # Only lockfile_present should pass with this fixture.
    assert snap.posture_checks_passing == 1


@pytest.mark.asyncio
async def test_run_assessment_on_path_returns_assessment_even_when_osv_is_down(
    planted_repo: Path,
) -> None:
    gh = AsyncMock()
    gh.get_branch_protection.return_value = None
    gh.list_recent_commits.return_value = []

    osv = AsyncMock()
    osv.lookup.side_effect = RuntimeError("osv down")

    result = await run_assessment_on_path(
        planted_repo,
        repo_url="https://github.com/acme/demo",
        gh_client=gh,
        osv=osv,
        ghsa=None,
    )

    # Still produces a result; findings empty due to fallback sentinel.
    assert result.findings == []
    # Posture checks still ran.
    assert len(result.posture_checks) == 7


@pytest.mark.asyncio
async def test_run_assessment_on_path_flags_critical_severity() -> None:
    # Minimal repo with a single dep + a CRITICAL advisory.
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "package-lock.json").write_text(
            json.dumps(
                {
                    "lockfileVersion": 3,
                    "packages": {"node_modules/evil": {"version": "1.0.0"}},
                }
            )
        )
        gh = AsyncMock()
        gh.get_branch_protection.return_value = {"allow_force_pushes": {"enabled": False}}
        gh.list_recent_commits.return_value = []

        critical = Advisory(
            id="GHSA-xxxx-yyyy-zzzz",
            summary="critical",
            severity="CRITICAL",
            fixed_version="1.0.1",
            raw={},
        )
        osv = AsyncMock()
        osv.lookup.return_value = [critical]

        result = await run_assessment_on_path(
            repo,
            repo_url="https://github.com/a/b",
            gh_client=gh,
            osv=osv,
        )

    assert result.criteria_snapshot is not None
    assert result.criteria_snapshot.no_critical_vulns is False


def test_derive_grade_a_when_all_five_criteria_met() -> None:
    snap = CriteriaSnapshot(
        no_critical_vulns=True,
        posture_checks_passing=7,
        posture_checks_total=7,
        security_md_present=True,
        dependabot_present=True,
    )
    # All high-level criteria met: no criticals + no highs + branch_protection
    # + no secrets + SECURITY.md present.
    findings: list[dict] = []
    posture_statuses = {
        "branch_protection": "pass",
        "no_secrets_in_code": "pass",
    }
    assert derive_grade(snap, findings, posture_statuses) == "A"


def test_derive_grade_f_when_criticals_present() -> None:
    snap = CriteriaSnapshot(no_critical_vulns=False)
    findings = [{"raw_severity": "CRITICAL"}]
    posture_statuses = {"branch_protection": "fail", "no_secrets_in_code": "fail"}
    assert derive_grade(snap, findings, posture_statuses) == "F"
