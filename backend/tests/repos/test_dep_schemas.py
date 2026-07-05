"""SP1 Task 1 — DepNode / DepManifest schema."""

from __future__ import annotations

from cliff.repos.schemas import DepManifest, DepNode


def test_dep_node_roundtrips() -> None:
    n = DepNode(
        name="undici",
        version="7.16.0",
        ecosystem="npm",
        scopes=["dev"],
        direct=False,
        declared_in=[],
        import_name="undici",
        import_sites=[],
    )
    d = n.model_dump()
    assert d["name"] == "undici"
    assert d["scopes"] == ["dev"]
    assert DepNode(**d) == n


def test_dep_manifest_roundtrips_and_allows_extra() -> None:
    m = DepManifest(
        ecosystems=["npm"],
        workspaces=["package.json"],
        nodes=[DepNode(name="yaml", version="2.8.0", ecosystem="npm", scopes=["prod"])],
        unresolved=[],
    )
    d = m.model_dump()
    assert d["nodes"][0]["version"] == "2.8.0"
    # extra="allow": a newer builder may add a field
    m2 = DepManifest(ecosystems=["npm"], nodes=[], future_field=123)
    assert m2.model_dump()["future_field"] == 123


def test_import_name_none_is_representable() -> None:
    n = DepNode(name="some-dist", version="1.0", ecosystem="pypi", import_name=None)
    assert n.import_name is None
