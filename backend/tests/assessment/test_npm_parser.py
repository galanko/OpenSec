"""Tests for the npm lockfile parser (IMPL-0002 B1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from opensec.assessment.parsers.base import ParsedDependency
from opensec.assessment.parsers.npm import parse_npm_lockfile

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lockfiles" / "npm"

# Deps every fixture is expected to surface (name, version, ecosystem).
EXPECTED_COMMON = {
    ("lodash", "4.17.20"),
    ("braces", "3.0.2"),
    ("fill-range", "7.0.1"),
    ("to-regex-range", "5.0.1"),
}


@pytest.mark.parametrize("version_dir", ["v1", "v2", "v3"])
def test_npm_parser_extracts_every_dep_with_version(version_dir: str) -> None:
    lockfile = FIXTURES / version_dir / "package-lock.json"
    result = parse_npm_lockfile(lockfile)

    for dep in result:
        assert isinstance(dep, ParsedDependency)
        assert dep.ecosystem == "npm"
        assert dep.name
        assert dep.version

    surfaced = {(d.name, d.version) for d in result}
    assert EXPECTED_COMMON.issubset(surfaced), (
        f"{version_dir} missing expected deps; got {surfaced}"
    )


def test_npm_parser_handles_missing_version_gracefully(tmp_path: Path) -> None:
    """An entry without a `version` key must be skipped, not raise."""
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text(
        json.dumps(
            {
                "name": "x",
                "lockfileVersion": 1,
                "dependencies": {
                    "good": {"version": "1.0.0"},
                    "broken": {"resolved": "https://example/broken.tgz"},
                },
            }
        )
    )

    result = parse_npm_lockfile(lockfile)
    names = {d.name for d in result}
    assert "good" in names
    assert "broken" not in names


def test_npm_parser_is_stable_across_lockfile_versions() -> None:
    v1 = {(d.name, d.version) for d in parse_npm_lockfile(FIXTURES / "v1" / "package-lock.json")}
    v2 = {(d.name, d.version) for d in parse_npm_lockfile(FIXTURES / "v2" / "package-lock.json")}
    v3 = {(d.name, d.version) for d in parse_npm_lockfile(FIXTURES / "v3" / "package-lock.json")}
    assert v1 == v2 == v3


def test_npm_parser_rejects_unknown_lockfile_version(tmp_path: Path) -> None:
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text(json.dumps({"lockfileVersion": 99, "dependencies": {}}))
    with pytest.raises(ValueError, match="lockfileVersion"):
        parse_npm_lockfile(lockfile)
