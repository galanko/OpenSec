"""Deterministic PyPI lockfile/manifest parser + dist→import name map.

Builds the ``pypi`` portion of the :class:`~cliff.repos.deps.graph.DepGraph`.

Parse strategy (in preference order — a *resolved* lockfile wins because it
carries the full transitive graph **and** the resolved edges):

1. ``uv.lock`` (TOML): ``[[package]]`` entries → ``(name, version)`` nodes; each
   package's ``dependencies`` array → edges. Workspace members (``source`` is
   ``editable``/``virtual``) are the project itself; their ``dependencies`` /
   ``[package.optional-dependencies]`` / ``[package.dev-dependencies]`` become
   roots, scoped via :func:`classify_scope` on the owning ``pyproject.toml``.
2. ``poetry.lock`` (TOML): ``[[package]]`` + ``[package.dependencies]`` (a table
   of name→spec) → edges. Direct deps + scopes come from the sibling
   ``pyproject.toml`` poetry sections; ``groups`` is used as a safety fallback.
3. ``Pipfile.lock`` (JSON): flat ``default`` / ``develop`` maps → roots (no
   transitive edges exist in the format, so every entry is a root — conservative).
4. Declared-only fallback (no lock): ``pyproject.toml`` (PEP 621 + PEP 735 +
   poetry sections), ``requirements*.txt``, ``setup.cfg``, ``Pipfile``. Roots
   only, no transitive edges — a node simply has no children, which is the
   conservative (never-false-clear) shape.

Safety framing (ADR-0053): when an edge target is ambiguous (a bare name that
resolves to several locked versions) we **over-connect** to every candidate
rather than risk dropping a path that reaches production. We never fabricate a
node that is not present in the lock/manifest. Environment markers on edges are
ignored (kept) for the same reason — dropping a marked edge could hide a
shipping path on some interpreter.

Pure / deterministic. No network, no LLM. ``tomllib`` for TOML, ``json`` for
Pipfile.lock.
"""

from __future__ import annotations

import configparser
import json
import re
import tomllib
from pathlib import Path

from .graph import DepGraph
from .manifests import Manifest, classify_extra, classify_scope

NV = tuple[str, str]
_ECO = "pypi"

# ── PEP 503 normalization ─────────────────────────────────────────────────────
_NORM_RE = re.compile(r"[-_.]+")


def normalize_dist(name: str) -> str:
    """PEP 503 normalized dist name: lowercased, runs of ``-``/``_``/``.`` → ``-``."""
    return _NORM_RE.sub("-", name.strip()).lower()


# ── dist → import name ────────────────────────────────────────────────────────
# Keys are PEP-503-normalized dist names; values are the top-level import name.
DIST_TO_IMPORT: dict[str, str] = {
    # required exceptions (task spec)
    "pyyaml": "yaml",
    "beautifulsoup4": "bs4",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "python-dateutil": "dateutil",
    "msgpack-python": "msgpack",
    "protobuf": "google.protobuf",
    "pyjwt": "jwt",
    "python-multipart": "multipart",
    "typing-extensions": "typing_extensions",
    "attrs": "attr",
    "setuptools": "setuptools",
    # common additional exceptions (identity would be wrong)
    "opencv-python-headless": "cv2",
    "opencv-contrib-python": "cv2",
    "pillow-simd": "PIL",
    "scikit-image": "skimage",
    "python-dotenv": "dotenv",
    "python-jose": "jose",
    "python-ldap": "ldap",
    "python-slugify": "slugify",
    "python-magic": "magic",
    "websocket-client": "websocket",
    "psycopg2-binary": "psycopg2",
    "mysqlclient": "MySQLdb",
    "pymysql": "pymysql",
    "pycryptodome": "Crypto",
    "pycryptodomex": "Cryptodome",
    "grpcio": "grpc",
    "google-cloud-storage": "google.cloud.storage",
    "faiss-cpu": "faiss",
    "faiss-gpu": "faiss",
    "sqlalchemy": "sqlalchemy",
    "markdown": "markdown",
    "html5lib": "html5lib",
}

# Dists whose import name genuinely cannot be derived from the dist name
# (multiple top-level modules, or stub-only). Returning identity here would be
# wrong, so we return None and let the caller stay conservative.
_AMBIGUOUS: frozenset[str] = frozenset(
    {
        "pywin32",  # exposes win32api, win32con, pythoncom, … — no single import
        "backports",  # namespace shim, no importable top-level of its own
    }
)


def dist_to_import(dist_name: str) -> str | None:
    """Import name for a PyPI dist.

    Identity (normalized, ``-``→``_``) for the 1:1 majority; the curated map for
    known exceptions; ``None`` only for genuinely ambiguous/unmappable dists.
    Callers must NOT treat ``None`` as "not imported" — it means "unknown".
    """
    norm = normalize_dist(dist_name)
    if not norm:
        return None
    if norm in _AMBIGUOUS:
        return None
    if norm in DIST_TO_IMPORT:
        return DIST_TO_IMPORT[norm]
    return norm.replace("-", "_")


# ── requirement-string parsing ────────────────────────────────────────────────
_REQ_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$")


def _extract_pin(spec: str) -> str:
    """Return the pinned version if the spec contains ``==``/``===``, else ``""``."""
    for part in spec.split(","):
        part = part.strip()
        if part.startswith("=="):
            return part.lstrip("=").strip()
    return ""


def _parse_req_line(raw: str) -> tuple[str, str] | None:
    """Parse one requirement line → ``(normalized_name, version)`` or ``None``.

    Version is the pinned ``==`` version if present, else ``""`` (unknown).
    Comments, options (``-r``/``-e``/``--hash``/…), and markers are stripped.
    """
    line = raw.strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    # strip inline comment
    if " #" in line:
        line = line.split(" #", 1)[0].strip()
    # strip environment marker
    if ";" in line:
        line = line.split(";", 1)[0].strip()
    # 'name @ url' direct reference → keep the name portion
    if "@" in line:
        head = line.split("@", 1)[0].strip()
        if head:
            line = head
    if not line:
        return None
    m = _REQ_RE.match(line)
    if not m:
        return None
    return normalize_dist(m.group(1)), _extract_pin(m.group(2) or "")


# ── uv.lock ───────────────────────────────────────────────────────────────────
def _resolve_targets(dep: object, name_versions: dict[str, list[str]]) -> list[NV]:
    """Resolve a uv dependency entry to concrete ``(name, version)`` target(s).

    Bare name with a unique locked version → that version. Bare name with several
    locked versions (uv normally disambiguates, but be safe) → *all* of them
    (over-connect). Unknown name → no target (never fabricate a node)."""
    if not isinstance(dep, dict):
        return []
    name = normalize_dist(str(dep.get("name", "")))
    if not name:
        return []
    ver = dep.get("version")
    if ver is not None:
        return [(name, str(ver))]
    versions = name_versions.get(name, [])
    if len(versions) == 1:
        return [(name, versions[0])]
    return [(name, v) for v in versions]  # 0 → [], >1 → over-connect


def _root_manifest(src: dict, pyprojects: list[Manifest], root: Path) -> str:
    """Path of the ``pyproject.toml`` owning a uv workspace member ``source``."""
    path = str(src.get("editable") or src.get("virtual") or src.get("directory") or ".").strip("/")
    candidate = "pyproject.toml" if path in ("", ".") else f"{path}/pyproject.toml"
    norm = {m.path.replace("\\", "/"): m.path for m in pyprojects}
    if candidate in norm:
        return norm[candidate]
    if "pyproject.toml" in norm:
        return norm["pyproject.toml"]
    return candidate


def _parse_uv_lock(
    g: DepGraph, root: Path, lock_path: Path, manifests: list[Manifest], unresolved: list[str]
) -> bool:
    try:
        data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        unresolved.append(f"{_rel(root, lock_path)}: unparseable uv.lock ({exc.__class__.__name__})")
        return False
    packages = data.get("package") or []
    if not packages:
        # A header-only (empty) but syntactically-valid lock is not a parse
        # failure — uv emits one before first resolve. Defer to the next
        # strategy (poetry.lock / declared-only) instead of flagging it.
        return False

    name_versions: dict[str, list[str]] = {}
    for pkg in packages:
        n = normalize_dist(str(pkg.get("name", "")))
        if not n:
            continue
        v = str(pkg.get("version", ""))
        g.add_node(n, v, _ECO)
        name_versions.setdefault(n, [])
        if v not in name_versions[n]:
            name_versions[n].append(v)

    pyprojects = [m for m in manifests if m.kind == "pyproject.toml"]
    for pkg in packages:
        n = normalize_dist(str(pkg.get("name", "")))
        if not n:
            continue
        frm: NV = (n, str(pkg.get("version", "")))
        # edges from every dependency section of this package (transitive graph)
        for dep in pkg.get("dependencies") or []:
            for tgt in _resolve_targets(dep, name_versions):
                g.add_edge(frm, tgt)
        for grp in ("optional-dependencies", "dev-dependencies"):
            for deps in (pkg.get(grp) or {}).values():
                for dep in deps or []:
                    for tgt in _resolve_targets(dep, name_versions):
                        g.add_edge(frm, tgt)
        # roots: only the workspace members (the project itself)
        src = pkg.get("source")
        if isinstance(src, dict) and ("editable" in src or "virtual" in src):
            declared_in = _root_manifest(src, pyprojects, root)
            _uv_roots(g, pkg.get("dependencies") or [], name_versions,
                      classify_scope(declared_in, "project.dependencies"), declared_in)
            for extra_name, deps in (pkg.get("optional-dependencies") or {}).items():
                # a dev/docs/test-named extra is non-shipping tooling; a feature
                # extra (anthropic, postgres, …) ships when installed → optional.
                _uv_roots(g, deps or [], name_versions, classify_extra(extra_name), declared_in)
            for deps in (pkg.get("dev-dependencies") or {}).values():
                _uv_roots(g, deps or [], name_versions,
                          classify_scope(declared_in, "dependency-groups"), declared_in)
    return True


def _uv_roots(g: DepGraph, deps: list, name_versions: dict[str, list[str]], scope: str, declared_in: str) -> None:
    for dep in deps:
        for (n, v) in _resolve_targets(dep, name_versions):
            g.add_root(n, v, scope, declared_in, _ECO)


# ── poetry.lock ───────────────────────────────────────────────────────────────
def _poetry_group_scope(group: str) -> str:
    return {"main": "prod", "dev": "dev", "test": "test", "docs": "docs"}.get(group, "prod")


def _parse_poetry_lock(
    g: DepGraph, root: Path, lock_path: Path, manifests: list[Manifest], unresolved: list[str]
) -> bool:
    try:
        data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        unresolved.append(f"{_rel(root, lock_path)}: unparseable poetry.lock ({exc.__class__.__name__})")
        return False
    packages = data.get("package") or []
    if not packages:
        return False  # empty-but-valid lock → defer to next strategy

    name_versions: dict[str, list[str]] = {}
    groups_of: dict[str, set[str]] = {}
    for pkg in packages:
        n = normalize_dist(str(pkg.get("name", "")))
        if not n:
            continue
        v = str(pkg.get("version", ""))
        g.add_node(n, v, _ECO)
        name_versions.setdefault(n, [])
        if v not in name_versions[n]:
            name_versions[n].append(v)
        groups = pkg.get("groups")
        if groups is None:  # legacy poetry: single 'category'
            cat = pkg.get("category")
            groups = [cat] if cat else ["main"]
        groups_of.setdefault(n, set()).update(str(x) for x in groups)

    # edges: poetry [package.dependencies] is a table name→spec
    for pkg in packages:
        n = normalize_dist(str(pkg.get("name", "")))
        if not n:
            continue
        frm: NV = (n, str(pkg.get("version", "")))
        deps = pkg.get("dependencies")
        if isinstance(deps, dict):
            for dep_name in deps:
                dn = normalize_dist(dep_name)
                for v in name_versions.get(dn, []):
                    g.add_edge(frm, (dn, v))

    # roots: prefer the sibling pyproject's declared direct deps (accurate
    # direct-set + declared_in); fall back to lock 'groups' when unavailable.
    declared_in = _sibling_pyproject(lock_path, root, manifests)
    added = _poetry_roots_from_pyproject(g, root, declared_in, name_versions)
    if not added:
        lock_rel = _rel(root, lock_path)
        for n, groups in groups_of.items():
            for grp in groups:
                for v in name_versions.get(n, []):
                    g.add_root(n, v, _poetry_group_scope(grp), lock_rel, _ECO)
    return True


def _poetry_roots_from_pyproject(g: DepGraph, root: Path, pyproject_rel: str | None, name_versions: dict[str, list[str]]) -> int:
    if not pyproject_rel:
        return 0
    full = root / pyproject_rel
    try:
        data = tomllib.loads(full.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return 0
    count = 0
    for section, name, ver in _iter_pyproject_deps(data):
        versions = name_versions.get(name) or ([ver] if ver else [""])
        for v in versions:
            g.add_root(name, v, classify_scope(pyproject_rel, section), pyproject_rel, _ECO)
            count += 1
    return count


def _sibling_pyproject(lock_path: Path, root: Path, manifests: list[Manifest]) -> str | None:
    lock_dir = _rel(root, lock_path.parent).replace("\\", "/").strip("/")
    want = "pyproject.toml" if lock_dir in ("", ".") else f"{lock_dir}/pyproject.toml"
    for m in manifests:
        if m.kind == "pyproject.toml" and m.path.replace("\\", "/") == want:
            return m.path
    return None


# ── Pipfile.lock (JSON, flat) ─────────────────────────────────────────────────
def _parse_pipfile_lock(g: DepGraph, root: Path, lock_path: Path, unresolved: list[str]) -> bool:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        unresolved.append(f"{_rel(root, lock_path)}: unparseable Pipfile.lock ({exc.__class__.__name__})")
        return False
    rel = _rel(root, lock_path)
    found = False
    for section, cscope_section in (("default", "project.dependencies"), ("develop", "dependency-groups")):
        for name, meta in (data.get(section) or {}).items():
            n = normalize_dist(name)
            if not n:
                continue
            ver = ""
            if isinstance(meta, dict):
                vv = meta.get("version", "")
                if isinstance(vv, str) and vv.startswith("=="):
                    ver = vv.lstrip("=").strip()
            g.add_root(n, ver, classify_scope(rel, cscope_section), rel, _ECO)
            found = True
    return found  # empty-but-valid lock → defer to declared-only Pipfile


# ── declared-only fallback ────────────────────────────────────────────────────
def _poetry_spec_version(spec: object) -> str:
    if isinstance(spec, str):
        return _extract_pin(spec)
    if isinstance(spec, dict):
        v = spec.get("version", "")
        return _extract_pin(v) if isinstance(v, str) else ""
    return ""


def _iter_pyproject_deps(data: dict):
    """Yield ``(classify_section, normalized_name, version)`` for every declared
    dependency in a pyproject (PEP 621, PEP 735, and poetry sections)."""
    proj = data.get("project")
    if isinstance(proj, dict):
        for req in proj.get("dependencies") or []:
            p = _parse_req_line(req) if isinstance(req, str) else None
            if p:
                yield "project.dependencies", p[0], p[1]
        for reqs in (proj.get("optional-dependencies") or {}).values():
            for req in reqs or []:
                p = _parse_req_line(req) if isinstance(req, str) else None
                if p:
                    yield "project.optional-dependencies", p[0], p[1]
    for reqs in (data.get("dependency-groups") or {}).values():
        for req in reqs or []:
            if isinstance(req, str):
                p = _parse_req_line(req)
                if p:
                    yield "dependency-groups", p[0], p[1]
            # {include-group = "..."} entries carry no dist → skip
    poetry = (data.get("tool") or {}).get("poetry") or {}
    for name, spec in (poetry.get("dependencies") or {}).items():
        nn = normalize_dist(name)
        if nn and nn != "python":
            yield "tool.poetry.dependencies", nn, _poetry_spec_version(spec)
    for name, spec in (poetry.get("dev-dependencies") or {}).items():
        nn = normalize_dist(name)
        if nn and nn != "python":
            yield "tool.poetry.group.dev.dependencies", nn, _poetry_spec_version(spec)
    for grp, gdata in (poetry.get("group") or {}).items():
        for name, spec in ((gdata or {}).get("dependencies") or {}).items():
            nn = normalize_dist(name)
            if nn and nn != "python":
                yield f"tool.poetry.group.{grp}.dependencies", nn, _poetry_spec_version(spec)


def _parse_declared(g: DepGraph, root: Path, manifests: list[Manifest], unresolved: list[str]) -> None:
    for m in manifests:
        full = root / m.path
        try:
            text = full.read_text(encoding="utf-8")
        except OSError:
            unresolved.append(f"{m.path}: unreadable")
            continue
        if m.kind == "pyproject.toml":
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError:
                unresolved.append(f"{m.path}: unparseable pyproject.toml")
                continue
            for section, name, ver in _iter_pyproject_deps(data):
                g.add_root(name, ver, classify_scope(m.path, section), m.path, _ECO)
        elif m.kind == "requirements":
            section = Path(m.path).name  # classify_scope keys on the filename
            for line in text.splitlines():
                p = _parse_req_line(line)
                if p:
                    g.add_root(p[0], p[1], classify_scope(m.path, section), m.path, _ECO)
        elif m.kind == "setup.cfg":
            _parse_setup_cfg(g, m.path, text, unresolved)
        elif m.kind == "pipfile":
            _parse_pipfile_toml(g, m.path, text, unresolved)


def _parse_setup_cfg(g: DepGraph, path: str, text: str, unresolved: list[str]) -> None:
    cp = configparser.ConfigParser()
    try:
        cp.read_string(text)
    except configparser.Error:
        unresolved.append(f"{path}: unparseable setup.cfg")
        return
    if cp.has_option("options", "install_requires"):
        for line in cp.get("options", "install_requires").splitlines():
            p = _parse_req_line(line)
            if p:
                g.add_root(p[0], p[1], classify_scope(path, "project.dependencies"), path, _ECO)
    if cp.has_section("options.extras_require"):
        for _key, val in cp.items("options.extras_require"):
            for line in val.splitlines():
                p = _parse_req_line(line)
                if p:
                    g.add_root(p[0], p[1], classify_scope(path, "project.optional-dependencies"), path, _ECO)


def _parse_pipfile_toml(g: DepGraph, path: str, text: str, unresolved: list[str]) -> None:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        unresolved.append(f"{path}: unparseable Pipfile")
        return
    for section, cscope_section in (("packages", "project.dependencies"), ("dev-packages", "dependency-groups")):
        for name, spec in (data.get(section) or {}).items():
            nn = normalize_dist(name)
            if not nn:
                continue
            ver = ""
            if isinstance(spec, str) and spec.startswith("=="):
                ver = spec.lstrip("=").strip()
            elif isinstance(spec, dict):
                vv = spec.get("version", "")
                if isinstance(vv, str) and vv.startswith("=="):
                    ver = vv.lstrip("=").strip()
            g.add_root(nn, ver, classify_scope(path, cscope_section), path, _ECO)


# ── helpers ───────────────────────────────────────────────────────────────────
def _rel(root: Path, p: Path) -> str:
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return str(p)


# ── entry point ───────────────────────────────────────────────────────────────
def parse_pypi(root: Path, manifests: list[Manifest]) -> tuple[DepGraph, list[str]]:
    """Build the pypi portion of the dependency graph.

    Prefers a resolved lockfile (uv.lock → poetry.lock → Pipfile.lock) for the
    full transitive graph + edges; otherwise falls back to declared-only roots
    from pyproject/requirements/setup.cfg/Pipfile. Returns ``(graph, unresolved)``
    where ``unresolved`` lists artifacts that could not be parsed confidently.
    """
    root = Path(root)
    g = DepGraph()
    unresolved: list[str] = []
    py_manifests = [m for m in manifests if m.ecosystem == _ECO]

    # candidate lock directories: repo root + every pyproject/Pipfile directory
    lock_dirs: set[Path] = {Path(".")}
    for m in py_manifests:
        if m.kind in ("pyproject.toml", "pipfile"):
            lock_dirs.add(Path(m.path).parent)

    uv_locks: list[Path] = []
    poetry_locks: list[Path] = []
    pipfile_locks: list[Path] = []
    for d in sorted(lock_dirs, key=str):
        base = root / d
        if (base / "uv.lock").is_file():
            uv_locks.append(base / "uv.lock")
        if (base / "poetry.lock").is_file():
            poetry_locks.append(base / "poetry.lock")
        if (base / "Pipfile.lock").is_file():
            pipfile_locks.append(base / "Pipfile.lock")

    resolved = False
    for lp in uv_locks:
        if _parse_uv_lock(g, root, lp, py_manifests, unresolved):
            resolved = True
    if not resolved:
        for lp in poetry_locks:
            if _parse_poetry_lock(g, root, lp, py_manifests, unresolved):
                resolved = True
    if not resolved:
        for lp in pipfile_locks:
            if _parse_pipfile_lock(g, root, lp, unresolved):
                resolved = True
    if not resolved:
        _parse_declared(g, root, py_manifests, unresolved)

    return g, unresolved
