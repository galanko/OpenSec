"""Deterministic npm/JS lockfile parser (ADR-0053 §3, dep_manifest artifact).

Builds the npm portion of the dependency graph from lockfiles + workspace
``package.json`` files. Pure — no network, no LLM. Supports the three formats the
JS ecosystem actually ships:

* **pnpm-lock.yaml** (v9): ``importers:`` gives each workspace's declared deps with
  a pre-resolved ``version``; ``packages:`` is the deduplicated node set; ``snapshots:``
  carries the resolved dependency edges. Version strings can carry a peer suffix
  ``1.2.3(peer@4)`` — stripped to ``1.2.3``.
* **yarn.lock** — classic v1 (``name@range:`` blocks with ``version "x"``, NOT valid
  YAML → line parser) and berry v2+ (``__metadata`` header, ``@npm:`` descriptors,
  valid YAML → PyYAML).
* **package-lock.json** (v2/v3): ``packages`` object keyed by ``""`` and
  ``node_modules/<name>`` install paths.

SAFETY: a dependency is only cleared as dev-only noise if its ``(name, version)``
node carries NO prod scope. **Under-connecting a prod edge is the dangerous
direction** — it can make a shipping package look dev-only and get false-cleared.
So when a range→version resolution or an edge is ambiguous, this parser prefers to
OVER-connect (add the edge / add every candidate version as a prod root) rather
than miss one. It never fabricates a node absent from the lockfile.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import yaml

try:  # fast C loader when available; identical semantics to SafeLoader
    from yaml import CSafeLoader as _YamlLoader
except ImportError:  # pragma: no cover - pure-python fallback
    from yaml import SafeLoader as _YamlLoader

from .graph import DepGraph
from .manifests import Manifest, classify_scope, discover_manifests
from .manifests import _SKIP_DIRS  # noqa: PLC2701 - shared walk-exclusion set

NV = tuple[str, str]

# npm dependency sections we read from a first-party package.json / importer.
_SECTIONS = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
# transitive edge sections we follow inside the lockfile (peer deps are provided
# by the consumer, so they are NOT transitive install edges).
_EDGE_SECTIONS = ("dependencies", "optionalDependencies")

# version strings that are workspace/local/non-registry refs — not resolvable to a
# published (name, version) node, so they are not emitted as external roots.
_LOCAL_PREFIXES = ("link:", "file:", "workspace:", "portal:", "self:")


# ── name/version helpers ─────────────────────────────────────────────────────
def _strip_peer(version: str) -> str:
    """Drop a pnpm/berry peer suffix: ``1.2.3(react@18)`` → ``1.2.3``."""
    return str(version).split("(", 1)[0].strip()


def _split_key(key: str) -> tuple[str, str]:
    """Split a ``name@version`` lock key into ``(name, version)``, scope-aware.

    The leading ``@`` of a scoped name is NOT the separator: the version is what
    follows the LAST ``@``. Any peer suffix is stripped first.
    """
    base = _strip_peer(key)
    at = base.rfind("@")
    if at <= 0:  # no separator (or leading-@ only) — not a resolvable node key
        return base, ""
    return base[:at], base[at + 1 :]


def _is_local(version: str) -> bool:
    v = str(version)
    return any(v.startswith(p) for p in _LOCAL_PREFIXES)


# ── range → version resolution (yarn/npm; pnpm resolves itself) ───────────────
def _resolve_range(
    name: str,
    rng: str,
    by_descriptor: dict[str, str],
    versions_by_name: dict[str, set[str]],
    descriptor_candidates: list[str],
) -> list[str]:
    """Resolve a declared ``(name, range)`` to installed version(s).

    Tries the exact descriptor forms first (the common, unambiguous case). Falls
    back — safely OVER-connecting — when the descriptor is not found:
      * the range is itself an installed exact version → that version,
      * the name has exactly one installed version → that version,
      * else every installed version of the name (never miss the shipping one).
    Returns ``[]`` only when the name is absent from the lockfile (never invent).
    """
    for cand in descriptor_candidates:
        if cand in by_descriptor:
            return [by_descriptor[cand]]
    versions = versions_by_name.get(name)
    if not versions:
        return []
    bare = _strip_peer(rng)
    if bare in versions:  # range was an exact pinned version
        return [bare]
    if len(versions) == 1:
        return [next(iter(versions))]
    return sorted(versions)  # ambiguous → over-connect across all versions


# ── pnpm-lock.yaml (v9) ──────────────────────────────────────────────────────
def parse_pnpm_lock(text: str, lock_dir: str) -> tuple[set[NV], list[tuple[NV, NV]], list[tuple[str, str, str, str]]]:
    """Return ``(nodes, edges, roots)`` for a pnpm-lock.

    ``roots`` items are ``(name, version, section, manifest_path)`` — manifest_path
    is repo-relative (the importer dir joined onto ``lock_dir``).
    """
    doc = yaml.load(text, Loader=_YamlLoader) or {}
    nodes: set[NV] = set()
    edges: list[tuple[NV, NV]] = []
    roots: list[tuple[str, str, str, str]] = []

    # nodes: every deduplicated package identity
    for key in doc.get("packages", {}) or {}:
        name, ver = _split_key(key)
        if name and ver:
            nodes.add((name, ver))

    # edges: from resolved snapshots (fall back to any deps carried on packages)
    def _emit_edges(container: dict) -> None:
        for key, body in (container or {}).items():
            if not isinstance(body, dict):
                continue
            frm = _split_key(key)
            if not frm[0] or not frm[1]:
                continue
            nodes.add(frm)
            for section in _EDGE_SECTIONS:
                for dep_name, dep_ver in (body.get(section) or {}).items():
                    to = (dep_name, _strip_peer(dep_ver))
                    if to[1]:
                        nodes.add(to)
                        edges.append((frm, to))

    _emit_edges(doc.get("snapshots", {}))
    _emit_edges(doc.get("packages", {}))  # older layouts inline deps on packages

    # roots: each importer (workspace) declaration, version pre-resolved by pnpm
    for importer, body in sorted((doc.get("importers", {}) or {}).items()):
        manifest_path = _join_manifest(lock_dir, importer)
        if not isinstance(body, dict):
            continue
        for section in _SECTIONS:
            for name, info in sorted((body.get(section) or {}).items()):
                version = info.get("version") if isinstance(info, dict) else info
                if version is None or _is_local(str(version)):
                    continue
                ver = _strip_peer(str(version))
                if ver:
                    roots.append((name, ver, section, manifest_path))
    return nodes, edges, roots


def _join_manifest(lock_dir: str, importer: str) -> str:
    """Repo-relative path of an importer's package.json."""
    if importer in (".", ""):
        base = lock_dir
    else:
        base = os.path.join(lock_dir, importer) if lock_dir else importer
    return os.path.normpath(os.path.join(base, "package.json")).replace("\\", "/")


# ── yarn.lock ────────────────────────────────────────────────────────────────
def _is_berry(text: str) -> bool:
    return "__metadata:" in text or bool(re.search(r"^\s+resolution:", text, re.M))


def _parse_yarn_berry(text: str) -> tuple[dict[str, str], dict[str, set[str]], set[NV], list[tuple[NV, str, str]]]:
    """Berry v2+ yarn.lock is valid YAML.

    Returns ``(by_descriptor, versions_by_name, nodes, edge_specs)`` where
    ``edge_specs`` are ``((from_name, from_ver), dep_name, dep_rangeval)``.
    """
    doc = yaml.load(text, Loader=_YamlLoader) or {}
    by_descriptor: dict[str, str] = {}
    versions_by_name: dict[str, set[str]] = {}
    nodes: set[NV] = set()
    edge_specs: list[tuple[NV, str, str]] = []

    for raw_key, body in doc.items():
        if raw_key == "__metadata" or not isinstance(body, dict):
            continue
        version = body.get("version")
        if version is None:
            continue
        version = _strip_peer(str(version))
        descriptors = [d.strip() for d in str(raw_key).split(",")]
        name = _berry_name(descriptors[0]) if descriptors else None
        resolution = body.get("resolution")
        if resolution:  # canonical (name, version) from the resolution field
            name = _berry_name(str(resolution)) or name
        if not name:
            continue
        node = (name, version)
        nodes.add(node)
        versions_by_name.setdefault(name, set()).add(version)
        for desc in descriptors:
            by_descriptor[desc] = version
        for section in _EDGE_SECTIONS:
            for dep_name, dep_val in (body.get(section) or {}).items():
                edge_specs.append((node, dep_name, str(dep_val)))
    return by_descriptor, versions_by_name, nodes, edge_specs


def _berry_name(descriptor: str) -> str:
    """Name from a berry descriptor/resolution: ``@scope/x@npm:1.2`` → ``@scope/x``."""
    at = descriptor.rfind("@")
    return descriptor[:at] if at > 0 else descriptor


def _parse_yarn_classic(text: str) -> tuple[dict[str, str], dict[str, set[str]], set[NV], list[tuple[NV, str, str]]]:
    """Classic v1 yarn.lock — line parser (``version "x"`` is not valid YAML)."""
    by_descriptor: dict[str, str] = {}
    versions_by_name: dict[str, set[str]] = {}
    nodes: set[NV] = set()
    edge_specs: list[tuple[NV, str, str]] = []

    blocks: list[tuple[list[str], str | None, list[tuple[str, str]]]] = []
    cur_keys: list[str] | None = None
    cur_ver: str | None = None
    cur_deps: list[tuple[str, str]] = []
    in_deps = False

    def flush() -> None:
        if cur_keys is not None:
            blocks.append((cur_keys, cur_ver, cur_deps))

    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0 and line.rstrip().endswith(":"):
            flush()
            header = line.rstrip()[:-1]
            cur_keys = [_unquote(k.strip()) for k in header.split(",")]
            cur_ver = None
            cur_deps = []
            in_deps = False
            continue
        if cur_keys is None:
            continue
        stripped = line.strip()
        if indent == 2:
            in_deps = False
            m = re.match(r'version:?\s+"?([^"\s]+)"?', stripped)
            if m:
                cur_ver = m.group(1)
            elif stripped in ("dependencies:", "optionalDependencies:"):
                in_deps = True
        elif indent >= 4 and in_deps:
            m = re.match(r'("?[^"\s]+"?)\s+"?([^"]+?)"?$', stripped)
            if m:
                cur_deps.append((_unquote(m.group(1)), _unquote(m.group(2))))
    flush()

    for keys, ver, deps in blocks:
        if not ver:
            continue
        ver = _strip_peer(ver)
        name = _classic_name(keys[0]) if keys else None
        if not name:
            continue
        node = (name, ver)
        nodes.add(node)
        versions_by_name.setdefault(name, set()).add(ver)
        for k in keys:
            by_descriptor[k] = ver
        for dep_name, dep_range in deps:
            edge_specs.append((node, dep_name, dep_range))
    return by_descriptor, versions_by_name, nodes, edge_specs


def _classic_name(descriptor: str) -> str:
    at = descriptor.rfind("@")
    return descriptor[:at] if at > 0 else descriptor


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_yarn_lock(
    text: str, manifests_here: list[tuple[str, str, str, str]]
) -> tuple[set[NV], list[tuple[NV, NV]], list[tuple[str, str, str, str]]]:
    """Return ``(nodes, edges, roots)`` for a yarn.lock (classic or berry).

    ``manifests_here`` items are ``(name, range, section, manifest_path)`` — every
    dependency declared by a first-party package.json governed by this lockfile.
    """
    berry = _is_berry(text)
    by_descriptor, versions_by_name, nodes, edge_specs = (
        _parse_yarn_berry(text) if berry else _parse_yarn_classic(text)
    )

    def candidates(name: str, rng: str) -> list[str]:
        if berry:
            return [f"{name}@{rng}", f"{name}@npm:{rng}"]
        return [f"{name}@{rng}"]

    # edges: resolve each dep range against the descriptor map
    edges: list[tuple[NV, NV]] = []
    for frm, dep_name, dep_val in edge_specs:
        if _is_local(dep_val):
            continue
        for ver in _resolve_range(dep_name, dep_val, by_descriptor, versions_by_name, candidates(dep_name, dep_val)):
            to = (dep_name, ver)
            nodes.add(to)
            edges.append((frm, to))

    # roots: resolve each first-party declaration
    roots: list[tuple[str, str, str, str]] = []
    for name, rng, section, manifest_path in manifests_here:
        if _is_local(rng):
            continue
        for ver in _resolve_range(name, rng, by_descriptor, versions_by_name, candidates(name, rng)):
            roots.append((name, ver, section, manifest_path))
    return nodes, edges, roots


# ── package-lock.json (v2/v3) ────────────────────────────────────────────────
def _pl_name(key: str) -> str:
    """``node_modules/@scope/x`` → ``@scope/x`` (last node_modules segment)."""
    idx = key.rfind("node_modules/")
    return key[idx + len("node_modules/") :] if idx != -1 else key


def _pl_resolve(pkgs: dict, from_key: str, dep: str) -> str | None:
    """Node-style resolution of ``dep`` from the package installed at ``from_key``."""
    cur = from_key
    while True:
        cand = (cur + "/node_modules/" + dep) if cur else ("node_modules/" + dep)
        entry = pkgs.get(cand)
        if isinstance(entry, dict) and entry.get("version"):
            return entry.get("version")
        if not cur:
            return None
        idx = cur.rfind("/node_modules/")
        cur = cur[:idx] if idx != -1 else ""


def parse_package_lock(
    text: str, manifests_here: list[tuple[str, str, str, str, str]]
) -> tuple[set[NV], list[tuple[NV, NV]], list[tuple[str, str, str, str]]]:
    """Return ``(nodes, edges, roots)`` for a package-lock.json (v2/v3).

    ``manifests_here`` items are ``(name, range, section, manifest_path, pkg_key)``
    where ``pkg_key`` is the manifest dir relative to the lockfile (``""`` = root),
    used as the resolution origin in the install tree.
    """
    doc = json.loads(text)
    pkgs = doc.get("packages")
    nodes: set[NV] = set()
    edges: list[tuple[NV, NV]] = []
    roots: list[tuple[str, str, str, str]] = []
    if not isinstance(pkgs, dict):  # v1 (no packages map) — caller marks unresolved
        raise ValueError("package-lock has no 'packages' map (v1)")

    # nodes + edges: every installed package path
    for key, entry in pkgs.items():
        if not key.startswith("node_modules/") or not isinstance(entry, dict):
            continue
        version = entry.get("version")
        if not version:
            continue
        frm = (_pl_name(key), str(version))
        nodes.add(frm)
        for section in _EDGE_SECTIONS + ("peerDependencies",):
            for dep_name, _rng in (entry.get(section) or {}).items():
                dep_ver = _pl_resolve(pkgs, key, dep_name)
                if dep_ver:
                    to = (dep_name, str(dep_ver))
                    nodes.add(to)
                    edges.append((frm, to))

    # roots: resolve each first-party declaration through the install tree
    for name, rng, section, manifest_path, pkg_key in manifests_here:
        if _is_local(rng):
            continue
        ver = _pl_resolve(pkgs, pkg_key, name)
        if ver:
            roots.append((name, str(ver), section, manifest_path))
    return nodes, edges, roots


# ── package.json reading ─────────────────────────────────────────────────────
def _read_package_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _declared_deps(pkg: dict) -> list[tuple[str, str, str]]:
    """``(name, range, section)`` for every dependency section of a package.json."""
    out: list[tuple[str, str, str]] = []
    for section in _SECTIONS:
        block = pkg.get(section)
        if isinstance(block, dict):
            for name, rng in block.items():
                out.append((name, str(rng), section))
    return out


# ── lockfile discovery ───────────────────────────────────────────────────────
_LOCK_PRECEDENCE = ("pnpm-lock.yaml", "yarn.lock", "package-lock.json")


def _find_lockfiles(root: Path) -> dict[str, str]:
    """Repo-relative dir → chosen lockfile name (one per dir, by precedence)."""
    by_dir: dict[str, dict[str, str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        rel_dir = os.path.relpath(dirpath, root)
        rel_dir = "" if rel_dir == "." else rel_dir.replace("\\", "/")
        for fn in filenames:
            if fn in _LOCK_PRECEDENCE:
                by_dir.setdefault(rel_dir, {})[fn] = fn
    chosen: dict[str, str] = {}
    for rel_dir, found in by_dir.items():
        for name in _LOCK_PRECEDENCE:
            if name in found:
                chosen[rel_dir] = name
                break
    return chosen


def _nearest_lock_dir(manifest_dir: str, lock_dirs: set[str]) -> str | None:
    """Deepest lockfile dir that is an ancestor of (or equal to) ``manifest_dir``."""
    best: str | None = None
    for ld in lock_dirs:
        if manifest_dir == ld or manifest_dir.startswith(ld + "/") if ld else True:
            if best is None or len(ld) > len(best):
                best = ld
    return best


# ── orchestrator ─────────────────────────────────────────────────────────────
def parse_npm(root: Path, manifests: list[Manifest]) -> tuple[DepGraph, list[str]]:
    """Build the npm portion of the dependency graph from lockfiles + package.json.

    Returns ``(graph, unresolved)`` — ``unresolved`` lists manifest/lockfile paths
    that could not be parsed confidently (never invents resolutions for them).
    """
    root = Path(root)
    graph = DepGraph()
    unresolved: list[str] = []

    if not manifests:
        manifests = discover_manifests(root)
    npm_manifests = [m for m in manifests if m.ecosystem == "npm" and m.kind == "package.json"]

    lock_by_dir = _find_lockfiles(root)  # rel_dir -> lockfile name
    lock_dirs = set(lock_by_dir)

    def _add(nodes: set[NV], edges: list[tuple[NV, NV]], roots: list[tuple[str, str, str, str]]) -> None:
        for name, ver in nodes:
            graph.add_node(name, ver, "npm")
        for frm, to in edges:
            graph.add_edge(frm, to)
        for name, ver, section, manifest_path in roots:
            graph.add_root(name, ver, classify_scope(manifest_path, section), manifest_path, "npm")

    # group first-party package.json manifests under the lockfile that governs them
    manifest_dir_of: dict[str, str] = {}
    for m in npm_manifests:
        md = os.path.dirname(m.path).replace("\\", "/")
        manifest_dir_of[m.path] = md
    governed: dict[str, list[Manifest]] = {ld: [] for ld in lock_dirs}
    for m in npm_manifests:
        ld = _nearest_lock_dir(manifest_dir_of[m.path], lock_dirs)
        if ld is None:
            # a package.json with deps but no lockfile above it can't be resolved
            pkg = _read_package_json(root / m.path)
            if _declared_deps(pkg):
                unresolved.append(m.path)
        else:
            governed[ld].append(m)

    for lock_dir, lock_name in sorted(lock_by_dir.items()):
        lock_path = (root / lock_dir / lock_name) if lock_dir else (root / lock_name)
        rel_lock = os.path.join(lock_dir, lock_name).replace("\\", "/") if lock_dir else lock_name
        try:
            text = lock_path.read_text(encoding="utf-8")
        except OSError:
            unresolved.append(rel_lock)
            continue

        try:
            if lock_name == "pnpm-lock.yaml":
                # pnpm resolves its own workspace declarations via importers
                nodes, edges, roots = parse_pnpm_lock(text, lock_dir)
                _add(nodes, edges, roots)
            elif lock_name == "yarn.lock":
                decls: list[tuple[str, str, str, str]] = []
                for m in governed.get(lock_dir, []):
                    pkg = _read_package_json(root / m.path)
                    for name, rng, section in _declared_deps(pkg):
                        decls.append((name, rng, section, m.path))
                nodes, edges, roots = parse_yarn_lock(text, decls)
                _add(nodes, edges, roots)
            elif lock_name == "package-lock.json":
                decls_pl: list[tuple[str, str, str, str, str]] = []
                for m in governed.get(lock_dir, []):
                    pkg = _read_package_json(root / m.path)
                    md = manifest_dir_of[m.path]
                    pkg_key = md[len(lock_dir) + 1 :] if lock_dir and md != lock_dir else ("" if md == lock_dir else md)
                    for name, rng, section in _declared_deps(pkg):
                        decls_pl.append((name, rng, section, m.path, pkg_key))
                nodes, edges, roots = parse_package_lock(text, decls_pl)
                _add(nodes, edges, roots)
            else:  # pragma: no cover - precedence list is closed
                unresolved.append(rel_lock)
        except (ValueError, yaml.YAMLError, KeyError):
            unresolved.append(rel_lock)

    unresolved.sort()
    return graph, unresolved
