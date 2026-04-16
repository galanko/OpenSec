"""pip lockfile parsers (IMPL-0002 B2).

Two input formats:

- `Pipfile.lock` — JSON with `default` and `develop` sections. Each entry may
  have a `version` shaped like `"==1.2.3"`.
- `requirements.txt` — plaintext. We honour only exact pins (`name==version`)
  and skip everything else (unpinned, `-r` includes, `-e` editables, comments,
  CLI flags, blank lines). This is per PRD: we scan versions we know, we don't
  resolve.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pathlib import Path

_PINNED_RE = re.compile(
    r"""^
    \s*
    (?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)     # PEP 503-ish package name
    \s*==\s*
    (?P<version>[^\s;#]+)                     # anything up to comment/marker/space
    """,
    re.VERBOSE,
)


def parse_pipfile_lock(path: Path) -> list[ParsedDependency]:
    data = json.loads(path.read_text())
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
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "--")):
            # -r include, -e editable, --extra-index-url, etc.
            continue
        # Strip inline comment.
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        match = _PINNED_RE.match(line)
        if match is None:
            continue
        name = match.group("name")
        version = match.group("version").strip()
        out.setdefault((name, version), ParsedDependency(name, version, "pip"))
    return list(out.values())
