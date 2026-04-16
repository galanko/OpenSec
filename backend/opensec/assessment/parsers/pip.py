"""pip lockfile parsers — `Pipfile.lock` (JSON) and exact-pinned `requirements.txt`.

We honour only exact pins (`name==version`); unpinned / `-r` / `-e` /
comments / CLI flags / blank lines are skipped silently. This is a scanner,
not a resolver.
"""

from __future__ import annotations

import json
import re
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
