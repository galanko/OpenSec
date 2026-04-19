"""Tests for the go.sum parser (IMPL-0002 B3)."""

from __future__ import annotations

from pathlib import Path

from opensec.assessment.parsers.golang import parse_go_sum

FIXTURE = Path(__file__).parent.parent / "fixtures" / "lockfiles" / "go" / "go.sum"


def test_go_parser_deduplicates_mod_and_gomod_entries() -> None:
    deps = parse_go_sum(FIXTURE)
    entries = [(d.name, d.version) for d in deps]

    # Each (module, version) pair appears exactly once despite the `/go.mod` suffix.
    assert entries.count(("github.com/gin-gonic/gin", "v1.7.7")) == 1
    assert entries.count(("github.com/stretchr/testify", "v1.8.0")) == 1
    assert (
        entries.count(
            ("golang.org/x/crypto", "v0.0.0-20220622213112-05595931fe9d")
        )
        == 1
    )

    for dep in deps:
        assert dep.ecosystem == "go"


def test_go_parser_skips_malformed_lines(tmp_path: Path) -> None:
    f = tmp_path / "go.sum"
    f.write_text(
        "# comment line\n"
        "\n"
        "garbage\n"
        "github.com/ok/mod v1.0.0 h1:abc=\n"
    )
    deps = parse_go_sum(f)
    assert [(d.name, d.version) for d in deps] == [("github.com/ok/mod", "v1.0.0")]
