"""SP1 Task 3 — DepGraph scope propagation (prod dominates)."""

from __future__ import annotations

from cliff.repos.deps.graph import DepGraph


def test_undici_version_split() -> None:
    """karakeep reality: undici@6.23.0 is direct prod (packages/shared);
    undici@7.16.0 is transitive, pulled only via a dev tool → does NOT ship."""
    g = DepGraph()
    # direct prod dep resolves to 6.23.0
    g.add_root("undici", "6.23.0", "prod", "packages/shared/package.json", "npm")
    # a dev tool root pulls undici@7.16.0 transitively
    g.add_root("some-dev-tool", "1.0.0", "dev", "package.json", "npm")
    g.add_node("undici", "7.16.0", "npm")
    g.add_edge(("some-dev-tool", "1.0.0"), ("undici", "7.16.0"))

    scopes = g.propagate_scopes()
    assert scopes[("undici", "6.23.0")] == {"prod"}
    assert scopes[("undici", "7.16.0")] == {"dev"}  # the finding's version — safe
    assert g.direct_nodes() == {("undici", "6.23.0"), ("some-dev-tool", "1.0.0")}


def test_both_dev_and_prod_yields_prod() -> None:
    g = DepGraph()
    g.add_root("prod-app", "1.0", "prod", "apps/web/package.json", "npm")
    g.add_root("dev-tool", "1.0", "dev", "package.json", "npm")
    g.add_node("shared", "2.0", "npm")
    g.add_edge(("prod-app", "1.0"), ("shared", "2.0"))
    g.add_edge(("dev-tool", "1.0"), ("shared", "2.0"))
    scopes = g.propagate_scopes()
    assert scopes[("shared", "2.0")] == {"prod", "dev"}
    assert "prod" in scopes[("shared", "2.0")]  # prod dominates → treated as ships


def test_pure_transitive_via_prod_ships() -> None:
    g = DepGraph()
    g.add_root("prod-app", "1.0", "prod", "package.json", "npm")
    g.add_node("yaml", "2.8.0", "npm")
    g.add_edge(("prod-app", "1.0"), ("yaml", "2.8.0"))
    scopes = g.propagate_scopes()
    assert scopes[("yaml", "2.8.0")] == {"prod"}
    assert ("yaml", "2.8.0") not in g.direct_nodes()  # transitive, not declared


def test_declared_in_map() -> None:
    g = DepGraph()
    g.add_root("axios", "1.13.2", "prod", "apps/web/package.json", "npm")
    g.add_root("axios", "1.13.2", "prod", "apps/worker/package.json", "npm")
    m = g.declared_in_map()
    assert set(m[("axios", "1.13.2")]) == {"apps/web/package.json", "apps/worker/package.json"}
