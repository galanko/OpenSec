"""Go `go.sum` parser.

`go.sum` emits two hash lines per module@version pair (`h1:` and `/go.mod
h1:`). We dedupe on `(module, version)` so each logical dependency surfaces
once; malformed lines are skipped silently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opensec.assessment._fs import safe_read_text
from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pathlib import Path


def parse_go_sum(path: Path) -> list[ParsedDependency]:
    out: dict[tuple[str, str], ParsedDependency] = {}
    for raw_line in safe_read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        module = parts[0]
        version = parts[1].removesuffix("/go.mod")
        if not module or not version:
            continue
        out.setdefault((module, version), ParsedDependency(module, version, "go"))
    return list(out.values())
