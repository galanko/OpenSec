"""SP1 Task 8 — resolve_by_dep_manifest (pure, safety-critical)."""

from __future__ import annotations

from cliff.agents.triage_dep_manifest import _parse_location, resolve_by_dep_manifest


def _mf(*nodes: dict) -> dict:
    return {"ecosystems": ["npm"], "workspaces": [], "nodes": list(nodes), "unresolved": []}


def _node(name, version, scopes, *, import_name="x", import_sites=None, ecosystem="npm", declared_in=None):
    return {
        "name": name,
        "version": version,
        "ecosystem": ecosystem,
        "scopes": scopes,
        "direct": False,
        "declared_in": declared_in or [],
        "import_name": import_name,
        "import_sites": import_sites or [],
    }


def _finding(location: str) -> dict:
    return {"type": "dependency", "location": location, "scanner": "trivy"}


# ── the clear case ────────────────────────────────────────────────────────────
def test_dev_only_unimported_clears() -> None:
    mf = _mf(_node("webpack-dev-server", "4.15.2", ["dev"], import_sites=[]))
    out = resolve_by_dep_manifest(_finding("webpack-dev-server@4.15.2"), mf)
    assert out is not None
    assert out.verdict == "false_positive"
    assert out.provenance.exit_stage == "dep_manifest_resolver"


def test_docs_and_build_scopes_clear() -> None:
    mf = _mf(_node("sphinx-thing", "1.0.0", ["docs", "build"]))
    assert resolve_by_dep_manifest(_finding("sphinx-thing@1.0.0"), mf) is not None


# ── the block (never-clear) cases ─────────────────────────────────────────────
def test_prod_scope_blocks() -> None:
    mf = _mf(_node("axios", "1.13.2", ["prod"]))
    assert resolve_by_dep_manifest(_finding("axios@1.13.2"), mf) is None


def test_both_dev_and_prod_blocks() -> None:
    mf = _mf(_node("shared", "2.0.0", ["dev", "prod"]))
    assert resolve_by_dep_manifest(_finding("shared@2.0.0"), mf) is None


def test_optional_scope_blocks() -> None:
    mf = _mf(_node("fsevents", "2.3.0", ["optional"]))
    assert resolve_by_dep_manifest(_finding("fsevents@2.3.0"), mf) is None


def test_imported_in_firstparty_blocks() -> None:
    mf = _mf(_node("yaml", "2.8.0", ["dev"], import_sites=["src/app.ts:12"]))
    assert resolve_by_dep_manifest(_finding("yaml@2.8.0"), mf) is None


def test_import_name_none_blocks() -> None:
    mf = _mf(_node("some-dist", "1.0.0", ["dev"], import_name=None))
    assert resolve_by_dep_manifest(_finding("some-dist@1.0.0"), mf) is None


def test_empty_scopes_blocks() -> None:
    mf = _mf(_node("mystery", "1.0.0", []))
    assert resolve_by_dep_manifest(_finding("mystery@1.0.0"), mf) is None


def test_package_not_in_manifest_falls_through() -> None:
    mf = _mf(_node("other", "1.0.0", ["dev"]))
    assert resolve_by_dep_manifest(_finding("absent@9.9.9"), mf) is None


def test_version_mismatch_falls_through() -> None:
    # the undici split: 6.23.0 ships (prod); the finding is 7.16.0 (dev) — but if
    # only the prod node is present, the 7.16.0 finding must not match it.
    mf = _mf(_node("undici", "6.23.0", ["prod"]))
    assert resolve_by_dep_manifest(_finding("undici@7.16.0"), mf) is None


def test_cross_ecosystem_collision_blocks() -> None:
    mf = _mf(
        _node("yaml", "2.8.0", ["dev"], ecosystem="npm"),
        _node("yaml", "2.8.0", ["dev"], ecosystem="pypi"),
    )
    # two nodes match (name, version) → ambiguous → conservative
    assert resolve_by_dep_manifest(_finding("yaml@2.8.0"), mf) is None


def test_none_manifest() -> None:
    assert resolve_by_dep_manifest(_finding("x@1.0"), None) is None


# ── location parsing ──────────────────────────────────────────────────────────
def test_parse_scoped_location() -> None:
    assert _parse_location("@xmldom/xmldom@0.8.0") == ("@xmldom/xmldom", "0.8.0")
    assert _parse_location("yaml@2.8.0") == ("yaml", "2.8.0")
    assert _parse_location("noversion") is None


def test_scoped_package_clears() -> None:
    mf = _mf(_node("@xmldom/xmldom", "0.8.0", ["dev"], ecosystem="npm"))
    assert resolve_by_dep_manifest(_finding("@xmldom/xmldom@0.8.0"), mf) is not None
