"""First-party import-site scan — the pitfall-1 repo-wide grep.

``find_import_sites`` returns the shipping (non-test, non-docs) first-party source
lines that import a package by its *import name*. This is the second, independent
safety gate: even if a package's scope were mis-computed as dev-only, a non-empty
result blocks the clear. It scans by import name (version-agnostic), so a package
imported anywhere in shipping first-party is never dev-cleared.
"""

from __future__ import annotations

import os
import re

from .manifests import _BUILD_DIRS, _DOCS_DIRS, _SKIP_DIRS, _TEST_DIRS

_EXCLUDE_DIRS = _SKIP_DIRS | _TEST_DIRS | _DOCS_DIRS | _BUILD_DIRS

_NPM_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
_PY_EXT = {".py", ".pyi"}
# also treat these filename markers as test/non-ship regardless of directory
_TEST_FILE_RE = re.compile(r"(\.|_|-)(test|spec)\.|(^|/)(test|conftest)_|_test\.py$", re.I)

_MAX_SITES = 30


def _npm_pattern(import_name: str) -> re.Pattern:
    n = re.escape(import_name)
    # from 'name' | from 'name/sub' | require('name') | import('name')
    return re.compile(
        rf"""(?:from|import)\s*\(?\s*['"]{n}(?:/[^'"]*)?['"]"""
        rf"""|require\(\s*['"]{n}(?:/[^'"]*)?['"]"""
    )


def _py_pattern(import_name: str) -> re.Pattern:
    n = re.escape(import_name)
    # import name | import name.sub | from name import | from name.sub import
    return re.compile(rf"""^\s*(?:import\s+{n}(?:\.\w+)*|from\s+{n}(?:\.\w+)*\s+import)""", re.M)


def _is_test_file(rel: str) -> bool:
    return bool(_TEST_FILE_RE.search(rel.replace("\\", "/")))


# One-pass collectors — extract the imported top-level name from each import
# statement so the whole repo is scanned ONCE (the per-node call would re-walk).
_NPM_SPEC_RE = re.compile(
    r"""(?:from|import)\s*\(?\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]"""
)
_PY_IMPORT_RE = re.compile(r"""^\s*(?:import\s+(\w+)|from\s+(\w+)(?:\.\w+)*\s+import)""")


def _npm_spec_to_pkg(spec: str) -> str | None:
    if not spec or spec.startswith(".") or spec.startswith("/"):
        return None  # relative / absolute — not a package
    parts = spec.split("/")
    if spec.startswith("@"):
        return "/".join(parts[:2]) if len(parts) >= 2 else None  # @scope/name
    return parts[0]


def collect_import_sites(root, ecosystem: str) -> dict[str, list[str]]:  # noqa: ANN001 - Path
    """One walk of shipping first-party source → ``{package_or_import_name: [file:line, ...]}``.

    npm keys are package names (``lodash``, ``@scope/name``); pypi keys are
    top-level import names (``yaml``, ``aiohttp``). Callers match a node's
    ``import_name`` against these keys.
    """
    root = os.fspath(root)
    exts = _NPM_EXT if ecosystem == "npm" else _PY_EXT if ecosystem == "pypi" else set()
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
                        if "import" not in line and "require" not in line:
                            continue
                        if ecosystem == "npm":
                            m = _NPM_SPEC_RE.search(line)
                            if not m:
                                continue
                            pkg = _npm_spec_to_pkg(m.group(1) or m.group(2) or "")
                        else:
                            m = _PY_IMPORT_RE.match(line)
                            if not m:
                                continue
                            pkg = m.group(1) or m.group(2)
                        if not pkg:
                            continue
                        bucket = out.setdefault(pkg, [])
                        if len(bucket) < _MAX_SITES:
                            bucket.append(f"{rel}:{i}")
            except OSError:
                continue
    return out


def find_import_sites(root, import_name: str, ecosystem: str) -> list[str]:  # noqa: ANN001 - Path
    """Shipping first-party ``file:line`` sites that import ``import_name``."""
    if not import_name:
        return []
    root = os.fspath(root)
    if ecosystem == "npm":
        exts, pat, line_mode = _NPM_EXT, _npm_pattern(import_name), False
    elif ecosystem == "pypi":
        exts, pat, line_mode = _PY_EXT, _py_pattern(import_name), True
    else:
        return []

    sites: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in _EXCLUDE_DIRS]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in exts:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            if _is_test_file(rel):
                continue
            try:
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        # cheap prefilter before regex
                        if import_name not in line:
                            continue
                        if line_mode:
                            if pat.match(line):
                                sites.append(f"{rel}:{i}")
                        elif pat.search(line):
                            sites.append(f"{rel}:{i}")
                        if len(sites) >= _MAX_SITES:
                            return sites
            except OSError:
                continue
    return sites
