"""Posture checks package (IMPL-0002 B5).

`run_all_posture_checks` executes the seven checks frozen in Session 0's
`PostureCheckName` literal and returns a list of `PostureCheckCreate`
rows (one per name, in a stable order — useful for snapshot tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from opensec.models.posture_check import PostureCheckCreate

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.models.posture_check import PostureCheckStatus


@dataclass(frozen=True)
class RepoCoords:
    owner: str
    repo: str
    branch: str = "main"


@dataclass(frozen=True)
class PostureCheckResult:
    """Intermediate shape — `run_all_posture_checks` wraps these into
    `PostureCheckCreate` rows once the orchestrator supplies an assessment_id.
    """

    check_name: str
    status: PostureCheckStatus
    detail: dict[str, Any] | None = None


class _GithubAPI(Protocol):
    async def get_branch_protection(
        self, owner: str, repo: str, branch: str
    ) -> Any: ...

    async def list_recent_commits(
        self, owner: str, repo: str, branch: str, *, limit: int = 20
    ) -> Any: ...


async def run_all_posture_checks(
    repo_path: Path,
    *,
    gh_client: _GithubAPI,
    coords: RepoCoords,
    assessment_id: str = "",
) -> list[PostureCheckCreate]:
    from opensec.assessment.posture.branch import (
        check_branch_protection,
        check_no_force_pushes,
        check_signed_commits,
    )
    from opensec.assessment.posture.files import (
        check_dependabot_config,
        check_lockfile_present,
        check_security_md,
    )
    from opensec.assessment.posture.secrets import scan_for_secrets

    results: list[PostureCheckResult] = [
        await check_branch_protection(gh_client, coords),
        await check_no_force_pushes(gh_client, coords),
        await check_signed_commits(gh_client, coords),
        scan_for_secrets(repo_path),
        check_security_md(repo_path),
        check_lockfile_present(repo_path),
        check_dependabot_config(repo_path),
    ]
    return [
        PostureCheckCreate(
            assessment_id=assessment_id,
            check_name=r.check_name,  # type: ignore[arg-type]
            status=r.status,
            detail=r.detail,
        )
        for r in results
    ]


__all__ = ["PostureCheckResult", "RepoCoords", "run_all_posture_checks"]
