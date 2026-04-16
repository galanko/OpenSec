"""Shared types for lockfile parsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Ecosystem = Literal["npm", "pip", "go"]


@dataclass(frozen=True)
class ParsedDependency:
    """One lockfile entry with resolved version.

    Equality is `(ecosystem, name, version)` — duplicates across lockfiles or
    lockfile sections dedupe naturally via `set()`.
    """

    name: str
    version: str
    ecosystem: Ecosystem
