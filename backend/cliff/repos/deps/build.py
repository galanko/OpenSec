"""Assemble the ``dep_manifest`` artifact (SP1 Task 7).

Discover manifests → parse npm + pypi graphs (each ecosystem independently) →
propagate scopes → resolve import names → attach first-party import sites (one
walk per ecosystem) → emit a ``DepManifest`` dict.

Robustness: this builder runs in-process at scan time and parses *untrusted*
lockfiles. It MUST NOT raise — an uncaught parser error would fail the whole
profile build (``profile_status='error'``), which silently disables the code_map
gate, the dep_manifest gate, AND the Deep dive for that repo. Any per-ecosystem
failure is caught and recorded in ``unresolved``; the artifact is still emitted.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..schemas import DepManifest, DepNode
from .imports import collect_import_sites
from .manifests import discover_manifests
from .npm import parse_npm
from .pypi import dist_to_import, parse_pypi

logger = logging.getLogger(__name__)


def _import_name(name: str, ecosystem: str) -> str | None:
    if ecosystem == "npm":
        return name  # npm import name == package name (scoped kept)
    if ecosystem == "pypi":
        return dist_to_import(name)
    return None


def _lookup_key(iname: str, ecosystem: str) -> str:
    # pypi import sites are bucketed by TOP-LEVEL module; a dotted import name
    # (``google.protobuf``) must be looked up by its first component (``google``).
    return iname.split(".")[0] if ecosystem == "pypi" else iname


def _ecosystem_nodes(root: Path, ms: list, parser, eco: str) -> tuple[list[dict], list[str]]:
    """Parse one ecosystem into DepNode dicts + its unresolved manifests. Never raises."""
    try:
        graph, unresolved = parser(root, ms)
        node_map = graph.nodes
        if not node_map:
            return [], list(unresolved)
        scopes = graph.propagate_scopes()
        direct = graph.direct_nodes()
        declared = graph.declared_in_map()
        imports = collect_import_sites(root, eco)  # one walk per ecosystem
        nodes: list[dict] = []
        for (name, version), node_eco in node_map.items():
            iname = _import_name(name, node_eco)
            sites = imports.get(_lookup_key(iname, node_eco), []) if iname else []
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
        return nodes, list(unresolved)
    except Exception:  # noqa: BLE001 - a bad lockfile must not fail the whole profile
        logger.warning("dep_manifest: %s parse failed — recording as unresolved", eco, exc_info=True)
        return [], [f"<{eco}-parse-error>"]


def build_dep_manifest(root) -> dict:  # noqa: ANN001 - Path | str
    root = Path(root)
    try:
        manifests = discover_manifests(root)
    except Exception:  # noqa: BLE001 - never let discovery crash the profile build
        logger.warning("dep_manifest: manifest discovery failed", exc_info=True)
        return DepManifest(unresolved=["<discovery-error>"]).model_dump()

    npm_ms = [m for m in manifests if m.ecosystem == "npm"]
    py_ms = [m for m in manifests if m.ecosystem == "pypi"]
    nodes: list[dict] = []
    unresolved: list[str] = []
    ecosystems: list[str] = []
    for ms, parser, eco in ((npm_ms, parse_npm, "npm"), (py_ms, parse_pypi, "pypi")):
        if not ms:
            continue
        eco_nodes, eco_unresolved = _ecosystem_nodes(root, ms, parser, eco)
        unresolved.extend(eco_unresolved)
        if eco_nodes:
            ecosystems.append(eco)
            nodes.extend(eco_nodes)

    return DepManifest(
        ecosystems=ecosystems,
        workspaces=[m.path for m in manifests],
        nodes=nodes,
        unresolved=unresolved,
    ).model_dump()
