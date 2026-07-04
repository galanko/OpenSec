"""Project-profile artifact schemas (ADR-0053 §3).

The typed shapes the profile builders emit and the triage Deep dive (ADR-0052)
consumes. ``extra="allow"`` keeps them forward-compatible (a newer builder can
add a field without breaking an older reader); a breaking change bumps
``RepoDirManager.SCHEMA_VERSION`` and the artifact is rebuilt, not migrated.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# ── Profile the project ──────────────────────────────────────────────────────

RepoKind = Literal["library", "service", "cli", "self_hosted_app", "monolith", "unknown"]


class EntryPoint(BaseModel):
    model_config = {"extra": "allow"}
    kind: str  # http | cli | queue | deserializer | webhook | ...
    location: str | None = None  # file:line
    description: str | None = None


class RepoProfile(BaseModel):
    """``profile.json`` — what the project is and how it runs."""

    model_config = {"extra": "allow"}
    kind: RepoKind = "unknown"
    deployment: str | None = None
    internet_facing: bool | None = None  # tri-state: None = couldn't determine
    entry_points: list[EntryPoint] = []
    trust_boundary: str | None = None
    build_cmd: str | None = None
    run_cmd: str | None = None
    docker_present: bool = False
    dockerfile_path: str | None = None
    summary: str | None = None  # one plain-English paragraph for PROFILE.md


# ── Map the live code ────────────────────────────────────────────────────────

PathCategory = Literal[
    "ships", "test", "fixture", "example", "docs", "build", "vendored", "dead"
]


class PathClass(BaseModel):
    model_config = {"extra": "allow"}
    glob: str
    category: PathCategory
    reason: str | None = None


class CodeMap(BaseModel):
    """``code_map.json`` — what ships vs what doesn't."""

    model_config = {"extra": "allow"}
    ships_roots: list[str] = []
    excluded_roots: list[str] = []
    classified: list[PathClass] = []


# ── Map the dependencies ─────────────────────────────────────────────────────

DepScope = Literal["prod", "dev", "test", "docs", "build", "optional"]


class DepNode(BaseModel):
    """One resolved ``(name, version)`` node in the dependency graph.

    ``scopes`` is the union of the scope of every top-level root that can reach
    this node in the lockfile graph — ``prod`` dominates (if any prod root
    reaches it, it ships). ``import_sites`` are first-party *shipping* source
    lines that import it (repo-wide, non-test). See ADR-0053 §3.
    """

    model_config = {"extra": "allow"}
    name: str
    version: str
    ecosystem: str  # "npm" | "pypi"
    scopes: list[DepScope] = []
    direct: bool = False  # declared as a top-level dep in some manifest
    declared_in: list[str] = []  # manifest paths declaring it (empty for pure transitive)
    import_name: str | None = None  # resolved import name (None = could not resolve → don't clear)
    import_sites: list[str] = []  # first-party shipping "file:line" that import it


class DepManifest(BaseModel):
    """``dep_manifest.json`` — the lockfile-resolved dependency graph.

    Deterministic (lockfile/manifest parse, no LLM). Keyed by ``(name, version)``
    so a direct-prod ``undici@6.23.0`` and a transitive ``undici@7.16.0`` in the
    same lockfile are distinct nodes.
    """

    model_config = {"extra": "allow"}
    ecosystems: list[str] = []
    workspaces: list[str] = []  # manifest paths discovered
    nodes: list[DepNode] = []
    unresolved: list[str] = []  # manifests/lockfiles we could not parse confidently


# ── Review past issues ───────────────────────────────────────────────────────

FixCoverage = Literal["instance", "class", "none"]


class PriorIssue(BaseModel):
    model_config = {"extra": "allow"}
    id: str  # CVE / GHSA id
    root_cause_family: str | None = None
    fixed: FixCoverage | None = None
    summary: str | None = None


class ThreatHistory(BaseModel):
    """``threat.json`` — the repo's prior vulnerabilities and recurring weak spots."""

    model_config = {"extra": "allow"}
    prior_issues: list[PriorIssue] = []
    recurring_families: list[str] = []
    fertile_areas: list[str] = []
