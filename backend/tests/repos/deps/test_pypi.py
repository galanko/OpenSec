"""SP1 — PyPI lockfile/manifest parser + dist→import map.

Unit tests run against small committed fixtures; one integration test runs the
parser over the FULL real ``instructor`` clone (uv.lock) when it is available.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cliff.repos.deps.manifests import Manifest, discover_manifests
from cliff.repos.deps.pypi import dist_to_import, normalize_dist, parse_pypi

FIXTURES = Path(__file__).parent / "fixtures" / "pypi"
INSTRUCTOR = Path("/private/tmp/cliff-triage-work/clones/instructor-36394b835f")


# ── dist_to_import ────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "dist,expected",
    [
        ("aiohttp", "aiohttp"),  # 1:1 identity
        ("urllib3", "urllib3"),  # 1:1 identity (digits preserved)
        ("requests", "requests"),
        ("PyYAML", "yaml"),  # known exception, case-insensitive
        ("pyyaml", "yaml"),
        ("beautifulsoup4", "bs4"),
        ("Pillow", "PIL"),
        ("scikit-learn", "sklearn"),
        ("opencv-python", "cv2"),
        ("python-dateutil", "dateutil"),
        ("typing_extensions", "typing_extensions"),  # normalizes then maps
        ("attrs", "attr"),
        ("PyJWT", "jwt"),
        ("protobuf", "google.protobuf"),
        ("some-dashed-lib", "some_dashed_lib"),  # 1:1: dashes → underscores
    ],
)
def test_dist_to_import(dist: str, expected: str) -> None:
    assert dist_to_import(dist) == expected


def test_dist_to_import_unknown_ambiguous_is_none() -> None:
    # genuinely ambiguous dist (multiple top-level modules) → None, not identity
    assert dist_to_import("pywin32") is None
    assert dist_to_import("") is None


# ── normalize_dist (PEP 503) ──────────────────────────────────────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("PyYAML", "pyyaml"),
        ("typing_extensions", "typing-extensions"),
        ("Flask-SQLAlchemy", "flask-sqlalchemy"),
        ("zope.interface", "zope-interface"),
        ("a__b--c..d", "a-b-c-d"),
    ],
)
def test_normalize_dist(raw: str, expected: str) -> None:
    assert normalize_dist(raw) == expected


# ── uv.lock slice: resolved graph + edges ─────────────────────────────────────
def test_uv_lock_slice_nodes_and_edges() -> None:
    root = FIXTURES / "uvslice"
    manifests = [Manifest("pyproject.toml", "pypi", "pyproject.toml")]
    g, unresolved = parse_pypi(root, manifests)

    assert unresolved == []
    # nodes resolved with versions
    assert ("aiohttp", "3.13.5") in g.nodes
    assert ("urllib3", "2.6.3") in g.nodes
    assert ("aiohappyeyeballs", "2.6.1") in g.nodes

    # direct deps of the workspace root are roots (prod)
    assert ("aiohttp", "3.13.5") in g.direct_nodes()
    assert ("urllib3", "2.6.3") in g.direct_nodes()

    scopes = g.propagate_scopes()
    assert scopes[("aiohttp", "3.13.5")] == {"prod"}
    # transitive edge aiohttp → aiohappyeyeballs propagates prod (proves edges exist)
    assert scopes[("aiohappyeyeballs", "2.6.1")] == {"prod"}
    assert scopes[("frozenlist", "1.8.0")] == {"prod"}
    # a docs-named extra is non-shipping tooling → scoped docs, never prod
    assert scopes[("mkdocs", "1.6.1")] == {"docs"}


# ── declared-only fallback (no lockfile) ──────────────────────────────────────
def test_declared_only_requirements_doc_scope() -> None:
    root = FIXTURES / "reqdoc"
    manifests = [Manifest("requirements-doc.txt", "pypi", "requirements")]
    g, unresolved = parse_pypi(root, manifests)

    assert unresolved == []
    roots = {r.name: r for r in g.roots}
    # every declared dep became a docs-scoped root
    assert roots["sphinx"].scope == "docs"
    assert roots["sphinx"].version == "7.2.6"  # pinned version parsed
    assert roots["mkdocs"].scope == "docs"
    assert roots["mkdocs"].version == ""  # unpinned → unknown version
    assert roots["mkdocstrings-python"].scope == "docs"  # inline comment stripped
    assert roots["furo"].scope == "docs"  # env marker stripped
    # '-r other-constraints.txt' include line is ignored (not fabricated)
    assert "other-constraints" not in roots

    scopes = g.propagate_scopes()
    assert scopes[("sphinx", "7.2.6")] == {"docs"}


# ── integration: full real instructor clone via uv.lock ───────────────────────
@pytest.mark.skipif(not INSTRUCTOR.exists(), reason="instructor clone not present")
def test_integration_instructor_full_clone() -> None:
    manifests = discover_manifests(INSTRUCTOR)
    g, unresolved = parse_pypi(INSTRUCTOR, manifests)

    # uv.lock parsed cleanly → nothing unresolved
    assert unresolved == []

    names = {n for (n, _v) in g.nodes}
    # direct prod dep declared in pyproject [project.dependencies]
    assert "aiohttp" in names
    assert "urllib3" in names  # transitive via requests, multi-version in lock
    assert "requests" in names

    # aiohttp is a direct prod root and ships
    scopes = g.propagate_scopes()
    aiohttp_nvs = [(n, v) for (n, v) in g.nodes if n == "aiohttp"]
    assert aiohttp_nvs, "aiohttp node missing"
    assert any("prod" in scopes.get(nv, set()) for nv in aiohttp_nvs)
    assert any(nv in g.direct_nodes() for nv in aiohttp_nvs)

    # the resolved graph has real transitive edges (not just declared roots)
    assert any("prod" in s for nv, s in scopes.items() if nv[0] == "yarl")


def test_lockless_subproject_not_dropped_when_sibling_has_lock(tmp_path) -> None:
    """Per-directory precedence: subA has a uv.lock, subB has only a pyproject.
    subB's declared prod dep must still be parsed (a repo-global 'resolved' flag
    would drop it and risk a false clear of subB's shipping deps)."""
    (tmp_path / "subA").mkdir()
    (tmp_path / "subA" / "pyproject.toml").write_text('[project]\nname = "a"\nversion = "0.1"\n')
    (tmp_path / "subA" / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "a"\nversion = "0.1"\nsource = { editable = "." }\n'
    )
    (tmp_path / "subB").mkdir()
    (tmp_path / "subB" / "pyproject.toml").write_text(
        '[project]\nname = "b"\nversion = "0.1"\ndependencies = ["subb-prod-dep"]\n'
    )
    manifests = [
        Manifest("subA/pyproject.toml", "pypi", "pyproject.toml"),
        Manifest("subB/pyproject.toml", "pypi", "pyproject.toml"),
    ]
    g, _unresolved = parse_pypi(tmp_path, manifests)
    assert "subb-prod-dep" in {r.name for r in g.roots}  # subB not dropped
