"""Go `go.sum` parser (IMPL-0002 B3).

`go.sum` lists two hash lines per module@version pair:

    github.com/foo/bar v1.2.3 h1:...
    github.com/foo/bar v1.2.3/go.mod h1:...

We dedupe on `(module, version)` so each logical dependency surfaces once.
Lines we don't recognise (comments, blanks, malformed) are skipped silently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opensec.assessment.parsers.base import ParsedDependency

if TYPE_CHECKING:
    from pathlib import Path


def parse_go_sum(path: Path) -> list[ParsedDependency]:
    out: dict[tuple[str, str], ParsedDependency] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        # Expected shape: "<module> <version>[/go.mod] h1:<hash>"
        if len(parts) < 3:
            continue
        module = parts[0]
        version_token = parts[1]
        version = version_token.removesuffix("/go.mod")
        if not module or not version:
            continue
        out.setdefault((module, version), ParsedDependency(module, version, "go"))
    return list(out.values())
