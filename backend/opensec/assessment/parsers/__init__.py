"""Lockfile parser registry.

`detect_lockfiles(path)` walks the repo root once and returns every supported
lockfile it finds, paired with its ecosystem and parser. Callers should run
the walk once per assessment and share the result.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from opensec.assessment._fs import iter_repo_files
from opensec.assessment.parsers.base import Ecosystem, ParsedDependency
from opensec.assessment.parsers.golang import parse_go_sum
from opensec.assessment.parsers.npm import parse_npm_lockfile
from opensec.assessment.parsers.pip import (
    parse_pipfile_lock,
    parse_requirements_txt,
    parse_uv_lock,
)

ParserFn = Callable[[Path], list[ParsedDependency]]

_REGISTRY: dict[str, tuple[Ecosystem, ParserFn]] = {
    "package-lock.json": ("npm", parse_npm_lockfile),
    "Pipfile.lock": ("pip", parse_pipfile_lock),
    "requirements.txt": ("pip", parse_requirements_txt),
    "uv.lock": ("pip", parse_uv_lock),
    "go.sum": ("go", parse_go_sum),
}


def detect_lockfiles(repo_path: Path) -> list[tuple[Ecosystem, Path, ParserFn]]:
    hits: list[tuple[Ecosystem, Path, ParserFn]] = []
    for path in iter_repo_files(repo_path):
        entry = _REGISTRY.get(path.name)
        if entry is None:
            continue
        ecosystem, parser = entry
        hits.append((ecosystem, path, parser))
    return hits


__all__ = [
    "ParsedDependency",
    "ParserFn",
    "detect_lockfiles",
    "parse_go_sum",
    "parse_npm_lockfile",
    "parse_pipfile_lock",
    "parse_requirements_txt",
    "parse_uv_lock",
]
