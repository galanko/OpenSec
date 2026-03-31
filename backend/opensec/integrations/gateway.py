"""MCP Gateway — config generator for workspace MCP server integration (ADR-0018).

The gateway resolves which integrations are enabled, decrypts their credentials
from the vault, substitutes ``${credential:key_name}`` placeholders in MCP
config templates, and returns the resolved configs for inclusion in each
workspace's ``opencode.json``.

OpenCode manages MCP child processes directly — it reads the ``mcp`` section
from ``opencode.json`` and spawns/kills servers automatically. The gateway's
job is purely **config generation**.
"""

from __future__ import annotations

import copy
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from opensec.db.repo_integration import list_integrations
from opensec.integrations.audit import AuditEvent
from opensec.integrations.registry import get_registry_entry

if TYPE_CHECKING:
    import aiosqlite

    from opensec.integrations.audit import AuditLogger
    from opensec.integrations.vault import CredentialVault

logger = logging.getLogger(__name__)

_PLACEHOLDER_RE = re.compile(r"\$\{credential:([a-zA-Z0-9_]+)\}")


@dataclass
class ResolvedWorkspaceIntegration:
    """Metadata about a resolved integration for the workspace manifest."""

    integration_id: str
    provider_name: str
    registry_id: str
    action_tier: int = 0
    capabilities: list[str] = field(default_factory=list)
    status: str = "connected"


@dataclass
class WorkspaceMCPResult:
    """Result of resolving MCP configs for a workspace."""

    mcp_configs: dict[str, dict[str, Any]]
    integrations: list[ResolvedWorkspaceIntegration]


class MCPConfigResolver:
    """Resolves MCP server configurations for workspace opencode.json generation."""

    def __init__(
        self,
        vault: CredentialVault,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self._vault = vault
        self._audit = audit_logger

    async def resolve_workspace_mcp_configs(
        self, db: aiosqlite.Connection
    ) -> dict[str, dict[str, Any]]:
        """Resolve MCP configs for all enabled integrations.

        Returns a dict mapping integration registry ID -> resolved MCP config.
        Convenience wrapper around :meth:`resolve_workspace` for backward compat.
        """
        result = await self.resolve_workspace(db)
        return result.mcp_configs

    async def resolve_workspace(
        self, db: aiosqlite.Connection
    ) -> WorkspaceMCPResult:
        """Resolve MCP configs and integration metadata for a workspace.

        Returns :class:`WorkspaceMCPResult` with both the MCP config dict
        (for ``opencode.json``) and integration metadata list (for the
        ``workspace-integrations.json`` manifest).

        Only includes integrations that have:
        1. An entry in ``integration_config`` with ``enabled=True``
        2. A registry entry with non-null ``mcp_config``
        3. All required credentials stored in the vault

        Integrations that fail any check are silently skipped with a log warning.
        """
        integrations = await list_integrations(db)
        mcp_configs: dict[str, dict[str, Any]] = {}
        ws_integrations: list[ResolvedWorkspaceIntegration] = []

        for integration in integrations:
            if not integration.enabled:
                continue

            # Look up registry entry for MCP config template.
            registry_id = integration.provider_name.lower().replace(" ", "-")
            entry = get_registry_entry(registry_id)
            if entry is None or entry.mcp_config is None:
                logger.debug(
                    "Skipping integration %s (%s): no MCP config in registry",
                    integration.id,
                    integration.provider_name,
                )
                continue

            # Decrypt credentials.
            try:
                credentials = await self._vault.get_credentials_for_workspace(
                    integration.id
                )
            except Exception:
                logger.warning(
                    "Skipping integration %s (%s): failed to decrypt credentials",
                    integration.id,
                    integration.provider_name,
                    exc_info=True,
                )
                continue

            if not credentials:
                logger.warning(
                    "Skipping integration %s (%s): no credentials stored",
                    integration.id,
                    integration.provider_name,
                )
                continue

            # Resolve placeholders.
            resolved = self.resolve_placeholders(entry.mcp_config, credentials)

            # Check for unresolved placeholders.
            unresolved = _find_unresolved_placeholders(resolved)
            if unresolved:
                logger.warning(
                    "Skipping integration %s (%s): unresolved placeholders: %s",
                    integration.id,
                    integration.provider_name,
                    unresolved,
                )
                continue

            mcp_configs[entry.id] = resolved
            ws_integrations.append(
                ResolvedWorkspaceIntegration(
                    integration_id=integration.id,
                    provider_name=integration.provider_name,
                    registry_id=entry.id,
                    action_tier=integration.action_tier,
                    capabilities=entry.capabilities,
                )
            )

            # Emit audit event.
            if self._audit is not None:
                await self._audit.log(
                    AuditEvent(
                        event_type="mcp.config_resolved",
                        integration_id=integration.id,
                        provider_name=integration.provider_name,
                        status="success",
                    )
                )
            logger.info(
                "Resolved MCP config for %s (integration %s)",
                entry.id,
                integration.id,
            )

        return WorkspaceMCPResult(mcp_configs=mcp_configs, integrations=ws_integrations)

    @staticmethod
    def resolve_placeholders(
        mcp_config: dict[str, Any], credentials: dict[str, str]
    ) -> dict[str, Any]:
        """Replace ``${credential:key_name}`` placeholders with real values.

        Only substitutes within the ``env`` dict values. The ``command`` and
        ``args`` fields are preserved unchanged. Returns a deep copy — the
        original template is never mutated.
        """
        resolved = copy.deepcopy(mcp_config)
        env = resolved.get("env")
        if not isinstance(env, dict):
            return resolved

        for key, value in env.items():
            if not isinstance(value, str):
                continue
            env[key] = _PLACEHOLDER_RE.sub(
                lambda m: credentials.get(m.group(1), m.group(0)),
                value,
            )

        return resolved


def _find_unresolved_placeholders(config: dict[str, Any]) -> list[str]:
    """Return any ``${credential:...}`` placeholders still present in env values."""
    env = config.get("env")
    if not isinstance(env, dict):
        return []
    unresolved = []
    for value in env.values():
        if isinstance(value, str):
            unresolved.extend(_PLACEHOLDER_RE.findall(value))
    return unresolved
