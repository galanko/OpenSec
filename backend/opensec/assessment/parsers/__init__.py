"""Lockfile parser registry.

Detection is file-name based (cheap, deterministic). `detect_lockfiles(path)`
walks the repo root and returns every recognised lockfile it finds, along
with the parser that should handle it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from opensec.assessment.parsers.base import ParsedDependency
from opensec.assessment.parsers.golang import parse_go_sum
from opensec.assessment.parsers.npm import parse_npm_lockfile
from opensec.assessment.parsers.pip import (
    parse_pipfile_lock,
    parse_requirements_txt,
)

ParserFn = Callable[[Path], list[ParsedDependency]]

# File name (case-sensitive) -> parser. Order matters only for display; the
# detector returns the full set, the caller dedupes by (name, version).
_REGISTRY: dict[str, ParserFn] = {
    "package-lock.json": parse_npm_lockfile,
    "Pipfile.lock": parse_pipfile_lock,
    "requirements.txt": parse_requirements_txt,
    "go.sum": parse_go_sum,
}

# Depth at which we stop walking. Lockfiles live at repo root or one level
# deep in backends/frontends monorepos; we intentionally skip node_modules
# and vendor trees.
_SKIP_DIRS = frozenset(
    {"node_modules", "vendor", ".git", ".venv", "venv", "__pycache__", "dist", "build"}
)


def detect_lockfiles(repo_path: Path) -> list[tuple[str, Path, ParserFn]]:
    """Return `(ecosystem, file_path, parser)` for every supported lockfile."""
    hits: list[tuple[str, Path, ParserFn]] = []
    for path in _iter_candidate_files(repo_path):
        parser = _REGISTRY.get(path.name)
        if parser is None:
            continue
        hits.append((_ecosystem_for(path.name), path, parser))
    return hits


def _iter_candidate_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _ecosystem_for(filename: str) -> str:
    if filename == "package-lock.json":
        return "npm"
    if filename in {"Pipfile.lock", "requirements.txt"}:
        return "pip"
    if filename == "go.sum":
        return "go"
    return "unknown"


__all__ = [
    "ParsedDependency",
    "ParserFn",
    "detect_lockfiles",
    "parse_go_sum",
    "parse_npm_lockfile",
    "parse_pipfile_lock",
    "parse_requirements_txt",
]
