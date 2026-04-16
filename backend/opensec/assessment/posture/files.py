"""Filesystem posture checks: SECURITY.md, lockfile presence, dependabot.yml."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opensec.assessment.posture import PostureCheckResult

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.assessment.parsers import Ecosystem, ParserFn

_SECURITY_MD_PATHS = ("SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md")
_DEPENDABOT_PATHS = (".github/dependabot.yml", ".github/dependabot.yaml")


def check_security_md(repo_path: Path) -> PostureCheckResult:
    for candidate in _SECURITY_MD_PATHS:
        if (repo_path / candidate).is_file():
            return PostureCheckResult(
                check_name="security_md",
                status="pass",
                detail={"path": candidate},
            )
    return PostureCheckResult(
        check_name="security_md",
        status="fail",
        detail={"searched": list(_SECURITY_MD_PATHS)},
    )


def check_lockfile_present(
    repo_path: Path,
    pre_detected: list[tuple[Ecosystem, Path, ParserFn]] | None = None,
) -> PostureCheckResult:
    if pre_detected is None:
        from opensec.assessment.parsers import detect_lockfiles

        hits = detect_lockfiles(repo_path)
    else:
        hits = pre_detected
    if hits:
        return PostureCheckResult(
            check_name="lockfile_present",
            status="pass",
            detail={"lockfiles": [str(p.relative_to(repo_path)) for _, p, _ in hits]},
        )
    return PostureCheckResult(check_name="lockfile_present", status="fail", detail=None)


def check_dependabot_config(repo_path: Path) -> PostureCheckResult:
    for candidate in _DEPENDABOT_PATHS:
        if (repo_path / candidate).is_file():
            return PostureCheckResult(
                check_name="dependabot_config",
                status="pass",
                detail={"path": candidate},
            )
    return PostureCheckResult(
        check_name="dependabot_config",
        status="fail",
        detail={"searched": list(_DEPENDABOT_PATHS)},
    )
