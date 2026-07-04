"""Manifest discovery + scope classification.

``classify_scope`` maps a (manifest path, dependency section) to a scope. It is
**conservative**: a manifest living under a non-shipping directory (docs/,
examples/, test/, …) makes all its deps non-prod; an unrecognized section
defaults to ``prod`` (so we never *accidentally* clear something as dev-only).
This is safety-critical — a package wrongly scoped non-prod could be false-cleared
(the import-site gate is the second line of defence).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Directory segments whose manifests never ship to production.
_DOCS_DIRS = {"docs", "doc", "documentation", "website", "site", "examples", "example", "demo", "demos"}
_TEST_DIRS = {"test", "tests", "__tests__", "__mocks__", "spec", "specs", "e2e", "cypress", "playwright"}
_BUILD_DIRS = {"benchmark", "benchmarks", "bench", "storybook", ".storybook", "scripts", "tools", "tooling"}

# Dependency section -> scope. Unknown -> "prod" (conservative).
_SECTION_SCOPE: dict[str, str] = {
    # npm
    "dependencies": "prod",
    "devDependencies": "dev",
    "optionalDependencies": "optional",
    "peerDependencies": "prod",  # conservative: consumer is expected to provide it
    # python (normalized section keys)
    "project.dependencies": "prod",
    "project.optional-dependencies": "optional",
    "dependency-groups": "dev",
    "tool.poetry.dependencies": "prod",
    "tool.poetry.group.dev.dependencies": "dev",
    "tool.poetry.dev-dependencies": "dev",
    "requirements.txt": "prod",
    "requirements-dev.txt": "dev",
    "requirements-doc.txt": "docs",
    "requirements-docs.txt": "docs",
    "requirements-examples.txt": "docs",
    "requirements-example.txt": "docs",
    "requirements-test.txt": "test",
    "requirements-tests.txt": "test",
}


def _path_dir_scope(manifest_path: str) -> str | None:
    """Non-prod scope implied by the manifest's *directory*, else None."""
    parts = manifest_path.replace("\\", "/").split("/")[:-1]  # drop filename
    for seg in parts:
        s = seg.lower()
        if s in _DOCS_DIRS:
            return "docs"
        if s in _TEST_DIRS:
            return "test"
        if s in _BUILD_DIRS:
            return "build"
    return None


def classify_scope(manifest_path: str, section: str) -> str:
    """Scope for a dependency declared in ``section`` of ``manifest_path``.

    Directory dominates (a dep in a docs/ manifest is docs-scope regardless of
    section); otherwise the section maps per ``_SECTION_SCOPE``; unknown → prod.
    """
    dir_scope = _path_dir_scope(manifest_path)
    if dir_scope is not None:
        return dir_scope
    return _SECTION_SCOPE.get(section, "prod")


@dataclass(frozen=True)
class Manifest:
    path: str  # relative to repo root
    ecosystem: str  # "npm" | "pypi"
    kind: str  # package.json | pyproject.toml | requirements | pnpm-workspace | setup.cfg | pipfile


_SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".venv", "venv", "site-packages", ".tox", ".next", "__pycache__", "vendor"}

_NPM_NAMES = {"package.json"}
_PNPM_WS = {"pnpm-workspace.yaml", "pnpm-workspace.yml"}


def discover_manifests(root) -> list[Manifest]:  # noqa: ANN001 - Path
    """Every first-party manifest under ``root`` (node_modules/venv/etc excluded)."""
    root = os.fspath(root)
    out: list[Manifest] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            low = fn.lower()
            if fn in _NPM_NAMES:
                out.append(Manifest(rel, "npm", "package.json"))
            elif fn in _PNPM_WS:
                out.append(Manifest(rel, "npm", "pnpm-workspace"))
            elif fn == "pyproject.toml":
                out.append(Manifest(rel, "pypi", "pyproject.toml"))
            elif fn == "setup.cfg":
                out.append(Manifest(rel, "pypi", "setup.cfg"))
            elif fn == "Pipfile":
                out.append(Manifest(rel, "pypi", "pipfile"))
            elif low.startswith("requirements") and low.endswith(".txt"):
                out.append(Manifest(rel, "pypi", "requirements"))
    return out
