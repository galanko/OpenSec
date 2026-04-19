"""Tests for the pip lockfile parsers (IMPL-0002 B2)."""

from __future__ import annotations

from pathlib import Path

from opensec.assessment.parsers.pip import (
    parse_pipfile_lock,
    parse_requirements_txt,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "lockfiles" / "pip"


def test_pip_pipfile_lock_extracts_pinned_versions() -> None:
    deps = parse_pipfile_lock(FIXTURES / "Pipfile.lock")
    entries = {(d.name, d.version) for d in deps}

    # Both `default` and `develop` sections contribute.
    assert ("django", "3.2.0") in entries
    assert ("requests", "2.20.0") in entries
    assert ("pytest", "8.0.0") in entries

    # Entry without `version` key is skipped (not raised).
    assert all(name != "no-version-pkg" for name, _ in entries)

    for dep in deps:
        assert dep.ecosystem == "pip"


def test_pip_requirements_txt_pinned_only() -> None:
    deps = parse_requirements_txt(FIXTURES / "requirements.txt")
    entries = {(d.name, d.version) for d in deps}

    assert ("django", "3.2.0") in entries
    assert ("requests", "2.20.0") in entries
    assert ("urllib3", "1.26.5") in entries
    assert ("pyyaml", "6.0") in entries

    # Unpinned and includes/editables/blank/comment lines are skipped, not raised.
    for name, _ in entries:
        assert name not in {"flask", "uvicorn", "other-reqs.txt", "./local-pkg"}


def test_pip_parser_ignores_comments_and_editables(tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text(
        "# header comment\n"
        "\n"
        "-e git+https://example.com/thing#egg=thing\n"
        "--extra-index-url https://example.com/pypi\n"
        "foo==1.2.3\n"
    )
    deps = parse_requirements_txt(req)
    assert [(d.name, d.version) for d in deps] == [("foo", "1.2.3")]


UV_FIXTURES = FIXTURES / "uv"


def test_pip_uv_lock_extracts_registry_packages() -> None:
    from opensec.assessment.parsers.pip import parse_uv_lock

    deps = parse_uv_lock(UV_FIXTURES / "uv.lock")
    entries = {(d.name, d.version) for d in deps}

    # Real registry packages land.
    assert ("aiosqlite", "0.22.1") in entries
    assert ("cryptography", "46.0.6") in entries
    assert ("pytest", "9.0.2") in entries

    # Virtual / workspace / editable entries are dropped — they're repo-local
    # and not resolvable on OSV.
    for name in ("opensec", "myworkspace", "editable-pkg"):
        assert all(n != name for n, _ in entries), f"{name} should be skipped"

    for dep in deps:
        assert dep.ecosystem == "pip"


def test_pip_uv_lock_registered_for_detection() -> None:
    """``uv.lock`` must be in the detect_lockfiles registry, otherwise the
    engine silently skips Python projects that use uv (i.e. OpenSec itself).
    """
    from opensec.assessment.parsers import _REGISTRY

    assert "uv.lock" in _REGISTRY
    ecosystem, _ = _REGISTRY["uv.lock"]
    assert ecosystem == "pip"
