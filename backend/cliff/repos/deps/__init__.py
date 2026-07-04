"""Deterministic dependency-manifest builder (ADR-0053 §3, dep_manifest artifact).

Parses lockfiles/manifests across all workspaces into a graph keyed by
``(name, version)``, propagates scopes (prod dominates), finds first-party import
sites, and emits a ``DepManifest``. Pure — no LLM, no network.

The public entry point ``build_dep_manifest`` is assembled in ``build.py`` and
re-exported here (SP1 Task 7).
"""

from __future__ import annotations

from .graph import DepGraph, Root

__all__ = ["DepGraph", "Root", "build_dep_manifest"]


def build_dep_manifest(root):  # noqa: ANN001 - thin lazy re-export to avoid import cycle at package load
    from .build import build_dep_manifest as _impl

    return _impl(root)
