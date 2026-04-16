"""Posture-checks package.

`run_all_posture_checks` executes the seven checks frozen in Session 0's
`PostureCheckName` literal and returns them in a stable order.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from opensec.models.posture_check import PostureCheckCreate

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.assessment.parsers import Ecosystem, ParserFn
    from opensec.models.posture_check import PostureCheckName, PostureCheckStatus


@dataclass(frozen=True)
class RepoCoords:
    owner: str
    repo: str
    branch: str = "main"


@dataclass(frozen=True)
class PostureCheckResult:
    check_name: PostureCheckName
    status: PostureCheckStatus
    detail: dict[str, Any] | None = None


class GithubAPI(Protocol):
    async def get_branch_protection(
        self, owner: str, repo: str, branch: str
    ) -> Any: ...

    async def list_recent_commits(
        self, owner: str, repo: str, branch: str, *, limit: int = 20
    ) -> Any: ...


async def run_all_posture_checks(
    repo_path: Path,
    *,
    gh_client: GithubAPI,
    coords: RepoCoords,
    assessment_id: str = "",
    pre_detected_lockfiles: list[tuple[Ecosystem, Path, ParserFn]] | None = None,
) -> list[PostureCheckCreate]:
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
    from opensec.assessment.posture.secrets import scan_for_secrets

    # Fire the two REST calls in parallel; fetch branch protection once and
    # share it between the two checks that care.
    protection, commits = await asyncio.gather(
        gh_client.get_branch_protection(coords.owner, coords.repo, coords.branch),
        gh_client.list_recent_commits(coords.owner, coords.repo, coords.branch),
    )

    # Run filesystem checks off-loop so they don't block the REST coroutines.
    scan_task = asyncio.to_thread(scan_for_secrets, repo_path)
    security_md_task = asyncio.to_thread(check_security_md, repo_path)
    lockfile_task = asyncio.to_thread(
        check_lockfile_present, repo_path, pre_detected_lockfiles
    )
    dependabot_task = asyncio.to_thread(check_dependabot_config, repo_path)
    secrets_res, security_res, lockfile_res, dependabot_res = await asyncio.gather(
        scan_task, security_md_task, lockfile_task, dependabot_task
    )

    results: list[PostureCheckResult] = [
        build_branch_protection_result(protection, coords),
        build_no_force_pushes_result(protection),
        build_signed_commits_result(commits),
        secrets_res,
        security_res,
        lockfile_res,
        dependabot_res,
    ]
    return [
        PostureCheckCreate(
            assessment_id=assessment_id,
            check_name=r.check_name,
            status=r.status,
            detail=r.detail,
        )
        for r in results
    ]


__all__ = ["GithubAPI", "PostureCheckResult", "RepoCoords", "run_all_posture_checks"]
