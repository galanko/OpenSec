"""Integration registry — catalog of available integrations with setup guides.

Builtin entries are stored as JSON files in this directory. The registry is
loaded once at import time and cached in memory.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_REGISTRY_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class CredentialField(BaseModel):
    """Schema for a single credential field in an integration's setup form."""

    key_name: str
    label: str
    type: str = "password"  # "password", "text", "url"
    required: bool = True
    help_text: str | None = None
    placeholder: str | None = None


class RegistryEntry(BaseModel):
    """A single integration in the catalog."""

    id: str
    name: str
    adapter_type: str  # "finding_source", "ticketing", "ownership_context", "validation"
    description: str
    icon: str = "extension"  # Material Symbols icon name
    status: str = "coming_soon"  # "available", "coming_soon", "community"
    setup_guide_md: str = ""
    credentials_schema: list[CredentialField] = []
    capabilities: list[str] = []  # "collect", "enrich", "investigate", "update"
    docs_url: str | None = None
    mcp_config: dict | None = None  # MCP server config template (Phase I-1)


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------

_cache: list[RegistryEntry] | None = None


def load_registry(*, registry_dir: Path | None = None) -> list[RegistryEntry]:
    """Load all JSON registry entries from *registry_dir*."""
    global _cache  # noqa: PLW0603
    if _cache is not None and registry_dir is None:
        return _cache

    target_dir = registry_dir or _REGISTRY_DIR
    entries: list[RegistryEntry] = []

    for path in sorted(target_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            entries.append(RegistryEntry(**data))
        except Exception:
            logger.warning("Failed to load registry entry %s", path.name, exc_info=True)

    if registry_dir is None:
        _cache = entries

    return entries


def get_registry_entry(entry_id: str, *, registry_dir: Path | None = None) -> RegistryEntry | None:
    """Look up a single registry entry by ID."""
    for entry in load_registry(registry_dir=registry_dir):
        if entry.id == entry_id:
            return entry
    return None


def clear_cache() -> None:
    """Clear the registry cache (useful for testing)."""
    global _cache  # noqa: PLW0603
    _cache = None
