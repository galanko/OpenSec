"""First-party import-site scan — the pitfall-1 repo-wide grep.

``collect_import_sites`` does ONE walk of shipping (non-test) first-party source
and buckets every import by the imported *top-level* name. This is the second,
independent safety gate: even if a package's scope were mis-computed as dev-only,
a non-empty result blocks the clear. It scans by import name (version-agnostic),
so a package imported anywhere in shipping first-party is never dev-cleared.
"""

from __future__ import annotations

import os
import re

from .manifests import _BUILD_DIRS, _DOCS_DIRS, _SKIP_DIRS, _TEST_DIRS

_EXCLUDE_DIRS = _SKIP_DIRS | _TEST_DIRS | _DOCS_DIRS | _BUILD_DIRS

_NPM_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
_PY_EXT = {".py", ".pyi"}
# test/non-ship file basenames, regardless of directory
_TEST_FILE_RE = re.compile(r"(\.|_|-)(test|spec)\.|(^|/)(test|conftest)_|_test\.py$", re.I)
_MAX_SITES = 30

# Matches the module specifier in `import x from 'spec'`, `require('spec')`,
# `import('spec')`, and re-exports `export ... from 'spec'`.
_NPM_SPEC_RE = re.compile(
    r"""(?:from|import)\s*\(?\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]"""
)
_PY_FROM_RE = re.compile(r"^\s*from\s+([A-Za-z_]\w*)")
_PY_IMPORT_RE = re.compile(r"^\s*import\s+(.+)")


def _is_test_file(rel: str) -> bool:
    return bool(_TEST_FILE_RE.search(rel.replace("\\", "/")))


def _npm_spec_to_pkg(spec: str) -> str | None:
    if not spec or spec.startswith(".") or spec.startswith("/"):
        return None  # relative / absolute — not a package
    parts = spec.split("/")
    if spec.startswith("@"):
        return "/".join(parts[:2]) if len(parts) >= 2 else None  # @scope/name
    return parts[0]


def _py_import_names(line: str) -> list[str]:
    """Top-level module names imported on a Python line.

    ``from a.b import c`` → ``["a"]``; ``import a.b, c as d`` → ``["a", "c"]``.
    Buckets by the TOP-LEVEL package so a dist whose import name is dotted
    (``protobuf`` → ``google.protobuf``) is found when callers look up ``google``.
    """
    m = _PY_FROM_RE.match(line)
    if m:
        return [m.group(1)]
    m = _PY_IMPORT_RE.match(line)
    if not m:
        return []
    names: list[str] = []
    for part in m.group(1).split(","):
        top = part.strip().split()[0].split(".")[0] if part.strip() else ""
        if top.isidentifier():
            names.append(top)
    return names


def collect_import_sites(root, ecosystem: str) -> dict[str, list[str]]:  # noqa: ANN001 - Path
    """One walk of shipping first-party source → ``{package_or_import_name: [file:line, ...]}``.

    npm keys are package names (``lodash``, ``@scope/name``); pypi keys are
    top-level import names (``yaml``, ``aiohttp``, ``google``). Callers match a
    node's ``import_name`` (top-level component, for pypi) against these keys.
    """
    root = os.fspath(root)
    is_npm = ecosystem == "npm"
    exts = _NPM_EXT if is_npm else _PY_EXT if ecosystem == "pypi" else set()
    if not exts:
        return {}
    out: dict[str, list[str]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in _EXCLUDE_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in exts:
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), root)
            if _is_test_file(rel):
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        # prefilter: `from`/`export … from` re-exports have "from"
                        # but not "import"/"require".
                        if "import" not in line and "require" not in line and "from" not in line:
                            continue
                        if is_npm:
                            m = _NPM_SPEC_RE.search(line)
                            pkgs = [_npm_spec_to_pkg(m.group(1) or m.group(2) or "")] if m else []
                        else:
                            pkgs = _py_import_names(line)
                        for pkg in pkgs:
                            if not pkg:
                                continue
                            bucket = out.setdefault(pkg, [])
                            if len(bucket) < _MAX_SITES:
                                bucket.append(f"{rel}:{i}")
            except OSError:
                continue
    return out
