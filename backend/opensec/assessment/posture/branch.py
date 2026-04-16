"""Branch-protection, force-push, and signed-commits checks (B5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from opensec.assessment.posture import PostureCheckResult
from opensec.assessment.posture.github_client import UnableToVerify

if TYPE_CHECKING:
    from opensec.assessment.posture import RepoCoords


async def check_branch_protection(gh_client: Any, coords: RepoCoords) -> PostureCheckResult:
    payload = await gh_client.get_branch_protection(
        coords.owner, coords.repo, coords.branch
    )
    if isinstance(payload, UnableToVerify):
        return PostureCheckResult(
            check_name="branch_protection",
            status="unknown",
            detail={"branch": coords.branch, "reason": payload.reason},
        )
    if payload is None:
        return PostureCheckResult(
            check_name="branch_protection",
            status="fail",
            detail={"branch": coords.branch, "reason": "no_protection_rule"},
        )
    return PostureCheckResult(
        check_name="branch_protection",
        status="pass",
        detail={"branch": coords.branch},
    )


async def check_no_force_pushes(gh_client: Any, coords: RepoCoords) -> PostureCheckResult:
    payload = await gh_client.get_branch_protection(
        coords.owner, coords.repo, coords.branch
    )
    if isinstance(payload, UnableToVerify):
        return PostureCheckResult(
            check_name="no_force_pushes",
            status="unknown",
            detail={"reason": payload.reason},
        )
    if payload is None:
        return PostureCheckResult(
            check_name="no_force_pushes",
            status="fail",
            detail={"reason": "no_protection_rule"},
        )
    force_setting = payload.get("allow_force_pushes")
    enabled = False
    if isinstance(force_setting, dict):
        enabled = bool(force_setting.get("enabled"))
    elif isinstance(force_setting, bool):
        enabled = force_setting
    return PostureCheckResult(
        check_name="no_force_pushes",
        status="fail" if enabled else "pass",
        detail={"allow_force_pushes": enabled},
    )


async def check_signed_commits(gh_client: Any, coords: RepoCoords) -> PostureCheckResult:
    commits = await gh_client.list_recent_commits(
        coords.owner, coords.repo, coords.branch
    )
    if isinstance(commits, UnableToVerify):
        return PostureCheckResult(
            check_name="signed_commits",
            status="unknown",
            detail={"reason": commits.reason},
        )
    if not commits:
        # No commits inspected — advisory, not fail.
        return PostureCheckResult(
            check_name="signed_commits",
            status="advisory",
            detail={"reason": "no_commits_inspected"},
        )

    total = len(commits)
    signed = sum(1 for c in commits if _is_signed(c))
    # Mixed => advisory per IMPL-0002: signed commits are an "advisory"
    # posture check, never a hard fail.
    status = "pass" if signed == total else "advisory"
    return PostureCheckResult(
        check_name="signed_commits",
        status=status,
        detail={"signed": signed, "total": total},
    )


def _is_signed(commit: dict[str, Any]) -> bool:
    commit_obj = commit.get("commit") or {}
    verification = commit_obj.get("verification") or {}
    return bool(verification.get("verified"))
