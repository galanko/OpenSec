"""Assemble the ``dep_manifest`` artifact (SP1 Task 7).

Discover manifests → parse npm + pypi graphs (each ecosystem independently) →
propagate scopes → resolve import names → attach first-party import sites (one
walk per ecosystem) → emit a ``DepManifest`` dict.
"""

from __future__ import annotations

from pathlib import Path

from ..schemas import DepManifest, DepNode
from .imports import collect_import_sites
from .manifests import discover_manifests
from .npm import parse_npm
from .pypi import dist_to_import, parse_pypi


def _import_name(name: str, ecosystem: str) -> str | None:
    if ecosystem == "npm":
        return name  # npm import name == package name (scoped kept)
    if ecosystem == "pypi":
        return dist_to_import(name)
    return None


def build_dep_manifest(root) -> dict:  # noqa: ANN001 - Path | str
    root = Path(root)
    manifests = discover_manifests(root)
    npm_ms = [m for m in manifests if m.ecosystem == "npm"]
    py_ms = [m for m in manifests if m.ecosystem == "pypi"]

    nodes: list[dict] = []
    unresolved: list[str] = []
    ecosystems: list[str] = []

    for ms, parser, eco in ((npm_ms, parse_npm, "npm"), (py_ms, parse_pypi, "pypi")):
        if not ms:
            continue
        graph, unres = parser(root, ms)
        unresolved.extend(unres)
        node_map = graph.nodes
        if not node_map:
            continue
        ecosystems.append(eco)
        scopes = graph.propagate_scopes()
        direct = graph.direct_nodes()
        declared = graph.declared_in_map()
        # one walk per ecosystem → {import_name/package: [file:line]}
        imports = collect_import_sites(root, eco)
        for (name, version), node_eco in node_map.items():
            iname = _import_name(name, node_eco)
            sites = imports.get(iname, []) if iname else []
            nodes.append(
                DepNode(
                    name=name,
                    version=version,
                    ecosystem=node_eco,
                    scopes=sorted(scopes.get((name, version), set())),
                    direct=(name, version) in direct,
                    declared_in=declared.get((name, version), []),
                    import_name=iname,
                    import_sites=sites,
                ).model_dump()
            )

    return DepManifest(
        ecosystems=ecosystems,
        workspaces=[m.path for m in manifests],
        nodes=nodes,
        unresolved=unresolved,
    ).model_dump()
