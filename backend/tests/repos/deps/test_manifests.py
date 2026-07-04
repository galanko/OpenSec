"""SP1 Task 2 — manifest discovery + scope classification."""

from __future__ import annotations

import pytest

from cliff.repos.deps.manifests import classify_scope, discover_manifests


@pytest.mark.parametrize(
    "path,section,expected",
    [
        ("package.json", "dependencies", "prod"),
        ("package.json", "devDependencies", "dev"),
        ("package.json", "optionalDependencies", "optional"),
        ("package.json", "peerDependencies", "prod"),
        ("apps/web/package.json", "dependencies", "prod"),
        # directory dominates section
        ("website/package.json", "dependencies", "docs"),
        ("docs/package.json", "dependencies", "docs"),
        ("examples/foo/package.json", "dependencies", "docs"),
        ("e2e/package.json", "dependencies", "test"),
        ("packages/api/__tests__/package.json", "dependencies", "test"),
        # python
        ("pyproject.toml", "project.dependencies", "prod"),
        ("pyproject.toml", "dependency-groups", "dev"),
        ("pyproject.toml", "project.optional-dependencies", "optional"),
        ("requirements.txt", "requirements.txt", "prod"),
        ("requirements-dev.txt", "requirements-dev.txt", "dev"),
        ("requirements-doc.txt", "requirements-doc.txt", "docs"),
        ("requirements-examples.txt", "requirements-examples.txt", "docs"),
        # unknown section defaults to prod (conservative)
        ("package.json", "someFutureSection", "prod"),
    ],
)
def test_classify_scope(path: str, section: str, expected: str) -> None:
    assert classify_scope(path, section) == expected


def test_discover_manifests(tmp_path) -> None:
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*\n")
    pkgs = tmp_path / "packages" / "api"
    pkgs.mkdir(parents=True)
    (pkgs / "package.json").write_text("{}")
    py = tmp_path / "sdk"
    py.mkdir()
    (py / "pyproject.toml").write_text("[project]\n")
    (tmp_path / "requirements-doc.txt").write_text("sphinx\n")
    # excluded
    nm = tmp_path / "node_modules" / "x"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text("{}")

    found = discover_manifests(tmp_path)
    paths = {m.path for m in found}
    assert "package.json" in paths
    assert "packages/api/package.json" in paths
    assert "sdk/pyproject.toml" in paths
    assert "requirements-doc.txt" in paths
    assert "pnpm-workspace.yaml" in paths
    # node_modules excluded
    assert not any("node_modules" in p for p in paths)
    ecos = {m.ecosystem for m in found}
    assert ecos == {"npm", "pypi"}
