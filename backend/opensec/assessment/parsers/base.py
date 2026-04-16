"""Shared types for lockfile parsers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Ecosystem = Literal["npm", "pip", "go"]


@dataclass(frozen=True)
class ParsedDependency:
    name: str
    version: str
    ecosystem: Ecosystem
