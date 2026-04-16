"""npm `package-lock.json` parser covering lockfile versions 1, 2, and 3.

- v1: entries live under `dependencies` (nested tree).
- v2: both `packages` (flat, node_modules/<name>) and `dependencies` are present;
      we read `packages` (authoritative) and ignore `dependencies`.
- v3: `packages` only.

The root package (`""` key in `packages`) is skipped. Entries without a
`version` are skipped (not raised) — missing versions are harmless metadata
holes, not parse failures.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pathlib import Path


def parse_npm_lockfile(path: Path) -> list[ParsedDependency]:
    data = json.loads(path.read_text())
    version = data.get("lockfileVersion")

    if version == 1:
        return _parse_v1(data.get("dependencies") or {})
    if version in (2, 3):
        return _parse_v2_or_v3(data.get("packages") or {})

    raise ValueError(f"Unsupported npm lockfileVersion: {version!r}")


def _parse_v1(deps: dict[str, Any]) -> list[ParsedDependency]:
    out: dict[tuple[str, str], ParsedDependency] = {}
    _walk_v1(deps, out)
    return list(out.values())


def _walk_v1(deps: dict[str, Any], out: dict[tuple[str, str], ParsedDependency]) -> None:
    for name, entry in deps.items():
        if not isinstance(entry, dict):
            continue
        version = entry.get("version")
        if isinstance(version, str) and version:
            out.setdefault((name, version), ParsedDependency(name, version, "npm"))
        nested = entry.get("dependencies")
        if isinstance(nested, dict):
            _walk_v1(nested, out)


def _parse_v2_or_v3(packages: dict[str, Any]) -> list[ParsedDependency]:
    out: dict[tuple[str, str], ParsedDependency] = {}
    for key, entry in packages.items():
        if not key:
            # Root package — not a dependency.
            continue
        if not isinstance(entry, dict):
            continue
        name = _name_from_packages_key(key, entry)
        version = entry.get("version")
        if not name or not isinstance(version, str) or not version:
            continue
        out.setdefault((name, version), ParsedDependency(name, version, "npm"))
    return list(out.values())


def _name_from_packages_key(key: str, entry: dict[str, Any]) -> str | None:
    """Derive package name from `node_modules/<...>` key, falling back to entry.name."""
    name_attr = entry.get("name")
    if isinstance(name_attr, str) and name_attr:
        return name_attr
    marker = "node_modules/"
    idx = key.rfind(marker)
    if idx == -1:
        return None
    return key[idx + len(marker) :] or None
