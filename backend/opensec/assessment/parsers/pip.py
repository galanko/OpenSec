"""pip lockfile parsers — `Pipfile.lock` (JSON), exact-pinned `requirements.txt`,
and `uv.lock` (TOML, astral-sh/uv).

We honour only exact pins (`name==version`); unpinned / `-r` / `-e` /
comments / CLI flags / blank lines are skipped silently. This is a scanner,
not a resolver.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import TYPE_CHECKING

from opensec.assessment._fs import safe_read_text
from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pathlib import Path

# PEP 503-ish name, `==`, then anything up to a marker/comment/whitespace.
_PINNED_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*(?P<version>[^\s;#]+)"
)


def parse_pipfile_lock(path: Path) -> list[ParsedDependency]:
    data = json.loads(safe_read_text(path))
    out: dict[tuple[str, str], ParsedDependency] = {}
    for section_name in ("default", "develop"):
        section = data.get(section_name) or {}
        for name, entry in section.items():
            if not isinstance(entry, dict):
                continue
            raw = entry.get("version")
            if not isinstance(raw, str):
                continue
            version = raw.lstrip("=").strip()
            if not version:
                continue
            out.setdefault((name, version), ParsedDependency(name, version, "pip"))
    return list(out.values())


def parse_uv_lock(path: Path) -> list[ParsedDependency]:
    """Parse ``uv.lock`` — astral-sh/uv's TOML lockfile.

    Shape (uv 0.4+):

        [[package]]
        name = "cryptography"
        version = "46.0.6"
        source = { registry = "https://pypi.org/simple" }

    Skip entries without a ``version`` (editable installs) and entries
    whose ``source`` is ``virtual`` or ``workspace`` — those are local
    packages in the repo, not runtime deps we can look up on OSV.
    """
    data = tomllib.loads(safe_read_text(path))
    out: dict[tuple[str, str], ParsedDependency] = {}
    for entry in data.get("package", []) or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        version = entry.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        source = entry.get("source")
        if isinstance(source, dict):
            if source.get("virtual") or source.get("editable"):
                continue
            # Workspace members are siblings of the root project — their
            # "version" is whatever the dev wrote in pyproject, not a
            # registry-resolvable version.
            if source.get("workspace") is True:
                continue
        out.setdefault((name, version), ParsedDependency(name, version, "pip"))
    return list(out.values())


def parse_requirements_txt(path: Path) -> list[ParsedDependency]:
    out: dict[tuple[str, str], ParsedDependency] = {}
    for raw_line in safe_read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "-", "--")):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        match = _PINNED_RE.match(line)
        if match is None:
            continue
        name = match.group("name")
        version = match.group("version").strip()
        out.setdefault((name, version), ParsedDependency(name, version, "pip"))
    return list(out.values())
