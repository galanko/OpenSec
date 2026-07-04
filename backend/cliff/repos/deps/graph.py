"""The resolved dependency graph — parser-agnostic structure + scope propagation.

A node is a ``(name, version)`` pair. A *root* is a node that some workspace
manifest declares as a top-level dependency, tagged with the scope it was
declared in (prod/dev/test/…). Edges point from a package to each package it
depends on (from the lockfile's resolved tree).

``propagate_scopes`` unions each root's scope onto every node reachable from it.
This is the load-bearing computation: a transitive node reachable from a prod
root ships (``prod`` in its scopes); one reachable only from dev roots does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

NV = tuple[str, str]  # (name, version)


@dataclass(frozen=True)
class Root:
    name: str
    version: str
    scope: str  # prod | dev | test | docs | build | optional
    declared_in: str  # manifest path


class DepGraph:
    def __init__(self) -> None:
        self._nodes: dict[NV, str] = {}  # (name, version) -> ecosystem
        self._edges: dict[NV, set[NV]] = {}  # (name, version) -> deps
        self.roots: list[Root] = []

    # ── construction ────────────────────────────────────────────────────────
    def add_node(self, name: str, version: str, ecosystem: str) -> None:
        nv = (name, version)
        self._nodes.setdefault(nv, ecosystem)
        self._edges.setdefault(nv, set())

    def add_root(self, name: str, version: str, scope: str, declared_in: str, ecosystem: str) -> None:
        self.add_node(name, version, ecosystem)
        self.roots.append(Root(name=name, version=version, scope=scope, declared_in=declared_in))

    def add_edge(self, frm: NV, to: NV) -> None:
        self._edges.setdefault(frm, set()).add(to)
        self._edges.setdefault(to, set())

    # ── queries ──────────────────────────────────────────────────────────────
    @property
    def nodes(self) -> dict[NV, str]:
        return self._nodes

    def direct_nodes(self) -> set[NV]:
        return {(r.name, r.version) for r in self.roots}

    def declared_in_map(self) -> dict[NV, list[str]]:
        out: dict[NV, list[str]] = {}
        for r in self.roots:
            out.setdefault((r.name, r.version), [])
            if r.declared_in not in out[(r.name, r.version)]:
                out[(r.name, r.version)].append(r.declared_in)
        return out

    def propagate_scopes(self) -> dict[NV, set[str]]:
        """Union each root's scope onto every node reachable from it (prod dominates
        by set membership — the resolver checks ``'prod' in scopes``)."""
        scopes: dict[NV, set[str]] = {nv: set() for nv in self._nodes}
        for root in self.roots:
            start: NV = (root.name, root.version)
            if start not in self._nodes:
                continue
            stack = [start]
            seen: set[NV] = set()
            while stack:
                nv = stack.pop()
                if nv in seen:
                    continue
                seen.add(nv)
                scopes.setdefault(nv, set()).add(root.scope)
                for dep in self._edges.get(nv, ()):  # traverse resolved edges
                    if dep not in seen:
                        stack.append(dep)
        return scopes
