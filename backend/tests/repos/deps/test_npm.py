"""SP1 — npm/JS lockfile parser (pnpm / yarn-classic / yarn-berry / package-lock).

Fixtures under ``fixtures/npm/`` are SMALL real slices of the actual lockfiles in
the triage clones (karakeep, mealie, linkwarden, nicegui). The final test runs the
parser over the FULL real karakeep clone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cliff.repos.deps.manifests import discover_manifests
from cliff.repos.deps.npm import (
    _split_key,
    _strip_peer,
    parse_npm,
)

FIX = Path(__file__).parent / "fixtures" / "npm"
KARAKEEP = Path("/private/tmp/cliff-triage-work/clones/karakeep-9879eb5d36")


def _build(fixture_dir: Path):
    """Run parse_npm over a fixture mini-repo → (graph, unresolved, scopes)."""
    manifests = discover_manifests(fixture_dir)
    graph, unresolved = parse_npm(fixture_dir, manifests)
    return graph, unresolved, graph.propagate_scopes()


# ── unit: name/version splitting ─────────────────────────────────────────────
@pytest.mark.parametrize(
    "key,name,ver",
    [
        ("undici@7.16.0", "undici", "7.16.0"),
        ("@xmldom/xmldom@0.8.0", "@xmldom/xmldom", "0.8.0"),  # scoped: @ in name
        ("@aws-sdk/client-s3@3.1014.0", "@aws-sdk/client-s3", "3.1014.0"),
        ("openai@6.34.0(ws@8.18.3)(zod@4.3.6)", "openai", "6.34.0"),  # peer suffix
    ],
)
def test_split_key(key: str, name: str, ver: str) -> None:
    assert _split_key(key) == (name, ver)


def test_strip_peer() -> None:
    assert _strip_peer("6.34.0(ws@8.18.3)(zod@4.3.6)") == "6.34.0"
    assert _strip_peer("6.23.0") == "6.23.0"


# ── pnpm (the primary format) ────────────────────────────────────────────────
def test_pnpm_undici_version_split() -> None:
    graph, unresolved, scopes = _build(FIX / "pnpm")
    assert unresolved == []

    undici_620 = ("undici", "6.23.0")
    undici_716 = ("undici", "7.16.0")
    # both versions are real resolved nodes
    assert undici_620 in graph.nodes
    assert undici_716 in graph.nodes
    # 6.23.0 is declared prod in packages/shared -> carries prod
    assert "prod" in scopes[undici_620]
    # 7.16.0 is only reachable via cheerio (a DEV dep of the root) -> NOT prod
    assert "prod" not in scopes[undici_716]
    assert scopes[undici_716] == {"dev"}


def test_pnpm_scoped_name_and_root() -> None:
    graph, _unresolved, scopes = _build(FIX / "pnpm")
    scoped = ("@xmldom/xmldom", "0.8.0")
    assert scoped in graph.nodes  # scoped name parsed correctly
    assert "prod" in scopes[scoped]
    # the prod root is declared in the shared workspace's package.json
    assert ("@xmldom/xmldom", "0.8.0") in graph.direct_nodes()
    decl = graph.declared_in_map()[("undici", "6.23.0")]
    assert decl == ["packages/shared/package.json"]


def test_pnpm_peer_suffix_stripped_on_root() -> None:
    graph, _unresolved, scopes = _build(FIX / "pnpm")
    # importer version was openai@6.34.0(ws@8.18.3)(zod@4.3.6) -> resolves to 6.34.0
    assert ("openai", "6.34.0") in graph.direct_nodes()
    assert "prod" in scopes[("openai", "6.34.0")]


def test_pnpm_dev_only_not_prod() -> None:
    _graph, _unresolved, scopes = _build(FIX / "pnpm")
    # cheerio is a dev-only workspace dep -> never carries prod
    assert scopes[("cheerio", "1.1.2")] == {"dev"}


# ── yarn classic v1 ──────────────────────────────────────────────────────────
def test_yarn_classic() -> None:
    graph, unresolved, scopes = _build(FIX / "yarn-classic")
    assert unresolved == []
    # axios is a prod dep; its range ^1.8.1 resolves to 1.17.0
    assert ("axios", "1.17.0") in graph.direct_nodes()
    assert "prod" in scopes[("axios", "1.17.0")]
    # transitive edge axios -> follow-redirects propagates prod
    assert "prod" in scopes[("follow-redirects", "1.16.0")]
    # scoped prod dep parses
    assert ("@mdi/js", "7.4.47") in graph.nodes
    assert "prod" in scopes[("@mdi/js", "7.4.47")]
    # dev-only dep does not carry prod
    assert "prod" not in scopes[("@types/node", "25.9.2")]


# ── yarn berry v2+ ───────────────────────────────────────────────────────────
def test_yarn_berry() -> None:
    graph, unresolved, scopes = _build(FIX / "yarn-berry")
    assert unresolved == []
    # prod deps of apps/web resolve through @npm: descriptors
    assert "prod" in scopes[("axios", "1.13.2")]
    assert "prod" in scopes[("next", "15.3.9")]
    assert "prod" in scopes[("dompurify", "3.3.1")]
    # real transitive edge dompurify -> @types/trusted-types propagates prod
    assert "prod" in scopes[("@types/trusted-types", "2.0.7")]
    # comma-joined scoped descriptor key resolves; dev-only -> not prod
    assert ("@types/react", "19.2.14") in graph.nodes
    assert "prod" not in scopes[("@types/react", "19.2.14")]


# ── package-lock v3 ──────────────────────────────────────────────────────────
def test_package_lock() -> None:
    graph, unresolved, scopes = _build(FIX / "package-lock")
    assert unresolved == []
    # prod dep resolves via the install tree
    assert "prod" in scopes[("dompurify", "3.4.0")]
    # scoped dev dep parses
    assert ("@antfu/install-pkg", "1.1.0") in graph.nodes
    assert "prod" not in scopes[("@antfu/install-pkg", "1.1.0")]
    # dev-only transitive stays non-prod
    assert ("package-manager-detector", "1.6.0") in graph.nodes
    assert "prod" not in scopes[("package-manager-detector", "1.6.0")]


# ── absent lockfile ──────────────────────────────────────────────────────────
def test_absent_lockfile_is_unresolved(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "x", "dependencies": {"axios": "^1.0.0"}})
    )
    graph, unresolved = parse_npm(tmp_path, discover_manifests(tmp_path))
    # no lockfile => cannot resolve => flagged, and nothing invented
    assert "package.json" in unresolved
    assert graph.nodes == {}


# ── integration: FULL real karakeep clone ────────────────────────────────────
@pytest.mark.skipif(not KARAKEEP.exists(), reason="karakeep triage clone not present")
def test_karakeep_full_clone_integration() -> None:
    """Reads the FULL karakeep clone (pnpm-lock v9, 27 workspaces)."""
    manifests = discover_manifests(KARAKEEP)
    graph, unresolved = parse_npm(KARAKEEP, manifests)  # (a) no exception
    # (b) the transitive undici@7.16.0 is a real resolved node
    assert ("undici", "7.16.0") in graph.nodes
    assert ("undici", "6.23.0") in graph.nodes
    # (c) the pnpm-lock parsed cleanly — nothing left unresolved
    assert unresolved == []
    # sanity: the prod root undici@6.23.0 is declared in packages/shared
    assert "packages/shared/package.json" in graph.declared_in_map()[("undici", "6.23.0")]
