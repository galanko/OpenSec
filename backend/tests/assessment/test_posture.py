"""Tests for posture checks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from opensec.assessment.posture import RepoCoords, run_all_posture_checks
from opensec.assessment.posture.branch import (
    build_branch_protection_result,
    build_no_force_pushes_result,
    build_signed_commits_result,
)
from opensec.assessment.posture.files import (
    check_dependabot_config,
    check_lockfile_present,
    check_security_md,
)
from opensec.assessment.posture.github_client import UnableToVerify
from opensec.assessment.posture.secrets import scan_for_secrets

if TYPE_CHECKING:
    from pathlib import Path

COORDS = RepoCoords(owner="acme", repo="app", branch="main")


# ---------------------------------------------------------------------------
# branch protection (pure builders — payload already fetched)
# ---------------------------------------------------------------------------


def test_branch_protection_check_reports_missing_rule_as_fail() -> None:
    result = build_branch_protection_result(None, COORDS)
    assert result.check_name == "branch_protection"
    assert result.status == "fail"
    assert result.detail and result.detail.get("branch") == "main"


def test_branch_protection_check_returns_unknown_when_forbidden() -> None:
    result = build_branch_protection_result(UnableToVerify(reason="forbidden"), COORDS)
    assert result.status == "unknown"


def test_branch_protection_check_pass_when_rule_present() -> None:
    protection = {
        "required_pull_request_reviews": {"required_approving_review_count": 1},
        "allow_force_pushes": {"enabled": False},
    }
    assert build_branch_protection_result(protection, COORDS).status == "pass"


def test_no_force_pushes_check_pass_when_protection_forbids() -> None:
    result = build_no_force_pushes_result({"allow_force_pushes": {"enabled": False}})
    assert result.status == "pass"


def test_no_force_pushes_check_fail_when_protection_allows() -> None:
    result = build_no_force_pushes_result({"allow_force_pushes": {"enabled": True}})
    assert result.status == "fail"


def test_signed_commits_check_advisory_when_unsigned_commits_found() -> None:
    commits = [
        {"sha": "a" * 40, "commit": {"verification": {"verified": True}}},
        {"sha": "b" * 40, "commit": {"verification": {"verified": False}}},
    ]
    assert build_signed_commits_result(commits).status == "advisory"


def test_signed_commits_check_pass_when_all_signed() -> None:
    commits = [{"sha": "a" * 40, "commit": {"verification": {"verified": True}}}]
    assert build_signed_commits_result(commits).status == "pass"


# ---------------------------------------------------------------------------
# secrets scan
# ---------------------------------------------------------------------------

# Synthetic values built from split literals so GitHub's secret scanner
# doesn't flag this file. Each value matches our regex but never appears
# whole in source.
_PLANTED_SECRETS = {
    "aws_akia": "AKIA" + "IOSFODNN7EXAMPLE",
    "github_ghp": "ghp" + "_" + "abcdefghijklmnopqrstuvwxyz0123456789",
    "github_ghs": "ghs" + "_" + "abcdefghijklmnopqrstuvwxyz0123456789",
    "stripe_sk_live": "sk" + "_live_" + "abcdefghijklmnopqrstuvwxyz012345",
    "google_aiza": "AI" + "za" + "SyA-0123456789012345678901234567890",
    "pem_block": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKC\n-----END RSA PRIVATE KEY-----\n",
}


@pytest.mark.parametrize("rule_name,value", list(_PLANTED_SECRETS.items()))
def test_secrets_scan_detects_known_patterns(
    tmp_path: Path, rule_name: str, value: str
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "leak.txt").write_text(f"token = '{value}'\n")
    result = scan_for_secrets(tmp_path)
    assert result.status == "fail"
    assert result.check_name == "no_secrets_in_code"
    hits = result.detail["matches"] if result.detail else []
    assert any(rule_name in str(hit.get("rule", "")) for hit in hits), (
        f"Rule {rule_name} not detected in {hits}"
    )


def test_secrets_scan_pass_when_no_patterns_match(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("hello world, no secrets here.\n")
    assert scan_for_secrets(tmp_path).status == "pass"


def test_secrets_scan_respects_opensec_ignore_file(tmp_path: Path) -> None:
    (tmp_path / ".opensec").mkdir()
    (tmp_path / ".opensec" / "secrets-ignore").write_text("samples/fake.txt\n")
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "fake.txt").write_text(
        f"key = '{_PLANTED_SECRETS['aws_akia']}'\n"
    )
    assert scan_for_secrets(tmp_path).status == "pass"


# ---------------------------------------------------------------------------
# filesystem checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "location", ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"]
)
def test_security_md_check_pass_if_file_exists_anywhere_standard(
    tmp_path: Path, location: str
) -> None:
    target = tmp_path / location
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Security\n")
    assert check_security_md(tmp_path).status == "pass"


def test_security_md_check_fail_when_absent(tmp_path: Path) -> None:
    assert check_security_md(tmp_path).status == "fail"


def test_lockfile_present_check_pass_if_any_supported_lockfile(tmp_path: Path) -> None:
    (tmp_path / "package-lock.json").write_text("{}")
    assert check_lockfile_present(tmp_path).status == "pass"


def test_lockfile_present_check_fail_when_absent(tmp_path: Path) -> None:
    assert check_lockfile_present(tmp_path).status == "fail"


def test_lockfile_present_uses_pre_detected_hits_without_re_walking(
    tmp_path: Path,
) -> None:
    fake_hit = ("npm", tmp_path / "package-lock.json", lambda _p: [])
    result = check_lockfile_present(tmp_path, pre_detected=[fake_hit])
    assert result.status == "pass"


@pytest.mark.parametrize(
    "filename", [".github/dependabot.yml", ".github/dependabot.yaml"]
)
def test_dependabot_config_check_pass_if_yaml_found(
    tmp_path: Path, filename: str
) -> None:
    target = tmp_path / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("version: 2\n")
    assert check_dependabot_config(tmp_path).status == "pass"


def test_dependabot_config_check_fail_when_absent(tmp_path: Path) -> None:
    assert check_dependabot_config(tmp_path).status == "fail"


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_all_returns_seven_checks_covering_every_name(tmp_path: Path) -> None:
    gh = AsyncMock()
    gh.get_branch_protection.return_value = None
    gh.list_recent_commits.return_value = []
    results = await run_all_posture_checks(tmp_path, gh_client=gh, coords=COORDS)
    names = {r.check_name for r in results}
    assert names == {
        "branch_protection",
        "no_force_pushes",
        "no_secrets_in_code",
        "security_md",
        "lockfile_present",
        "dependabot_config",
        "signed_commits",
    }
    assert len(results) == 7


@pytest.mark.asyncio
async def test_run_all_fetches_branch_protection_only_once(tmp_path: Path) -> None:
    gh = AsyncMock()
    gh.get_branch_protection.return_value = None
    gh.list_recent_commits.return_value = []
    await run_all_posture_checks(tmp_path, gh_client=gh, coords=COORDS)
    assert gh.get_branch_protection.await_count == 1
