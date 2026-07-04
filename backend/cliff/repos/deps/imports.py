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
