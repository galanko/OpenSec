"""Settings API endpoints — model, API keys, integrations, registry, credentials."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

from opensec.db.connection import get_db
from opensec.db.repo_integration import (
    create_integration,
    delete_integration,
    get_integration,
    list_integrations,
    update_integration,
)
from opensec.engine.config_manager import config_manager
from opensec.integrations.audit import AuditEvent
from opensec.integrations.connection_tester import run_connection_test
from opensec.integrations.health import IntegrationHealthMonitor
from opensec.integrations.registry import (
    RegistryEntry,
    get_registry_entry,
    load_registry,
)
from opensec.integrations.vault import CredentialKeyError
from opensec.models import (
    ApiKeyCreate,
    CredentialCreate,
    CredentialInfo,
    IntegrationConfig,
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    IntegrationHealthStatus,
    ModelConfig,
    ModelUpdateRequest,
    TestConnectionResult,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import aiosqlite

router = APIRouter(tags=["settings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _emit_audit(request: Request, **kwargs) -> None:
    """Emit an audit event if the audit logger is available."""
    audit_logger = getattr(request.app.state, "audit_logger", None)
    if audit_logger is not None:
        await audit_logger.log(AuditEvent(**kwargs))


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@router.get("/settings/model", response_model=ModelConfig)
async def get_model():
    try:
        return await config_manager.get_model()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode unavailable: {exc}") from exc


@router.put("/settings/model", response_model=ModelConfig)
async def update_model(body: ModelUpdateRequest, db=Depends(get_db)):
    try:
        return await config_manager.update_model(db, body.model_full_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode unavailable: {exc}") from exc


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


@router.get("/settings/providers")
async def list_providers():
    try:
        return await config_manager.list_available_providers()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode unavailable: {exc}") from exc


@router.get("/settings/providers/configured")
async def get_configured_providers():
    try:
        providers = await config_manager.get_configured_providers()
        auth = await config_manager.get_auth_status()
        return {"providers": providers, "auth": auth}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OpenCode unavailable: {exc}") from exc


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@router.get("/settings/api-keys")
async def list_api_keys(db=Depends(get_db)):
    return await config_manager.get_api_keys(db)


@router.put("/settings/api-keys/{provider}")
async def set_api_key(provider: str, body: ApiKeyCreate, db=Depends(get_db)):
    return await config_manager.set_api_key(db, provider, body.key)


@router.delete("/settings/api-keys/{provider}", status_code=204)
async def delete_api_key(provider: str, db=Depends(get_db)):
    deleted = await config_manager.delete_api_key(db, provider)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")


# ---------------------------------------------------------------------------
# Integration registry
# ---------------------------------------------------------------------------


@router.get("/settings/integrations/registry", response_model=list[RegistryEntry])
async def list_registry():
    """List all available integrations from the builtin registry."""
    return load_registry()


@router.get("/settings/integrations/registry/{entry_id}", response_model=RegistryEntry)
async def get_registry_entry_endpoint(entry_id: str):
    """Get a single registry entry with full setup guide."""
    entry = get_registry_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Registry entry not found")
    return entry


# ---------------------------------------------------------------------------
# Integrations CRUD (with audit instrumentation)
# ---------------------------------------------------------------------------


@router.get("/settings/integrations", response_model=list[IntegrationConfig])
async def list_integrations_endpoint(db=Depends(get_db)):
    return await list_integrations(db)


@router.post("/settings/integrations", response_model=IntegrationConfig, status_code=201)
async def create_integration_endpoint(
    body: IntegrationConfigCreate, request: Request, db=Depends(get_db)
):
    result = await create_integration(db, body)
    await _emit_audit(
        request,
        event_type="integration.create",
        integration_id=result.id,
        provider_name=body.provider_name,
        status="success",
    )
    return result


@router.put("/settings/integrations/{integration_id}", response_model=IntegrationConfig)
async def update_integration_endpoint(
    integration_id: str, body: IntegrationConfigUpdate, request: Request, db=Depends(get_db)
):
    result = await update_integration(db, integration_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Integration not found")
    await _emit_audit(
        request,
        event_type="integration.update",
        integration_id=integration_id,
        provider_name=result.provider_name,
        status="success",
    )
    return result


@router.delete("/settings/integrations/{integration_id}", status_code=204)
async def delete_integration_endpoint(
    integration_id: str, request: Request, db=Depends(get_db)
):
    # Cascade-delete credentials via vault if available.
    vault = getattr(request.app.state, "vault", None)
    if vault is not None:
        await vault.delete_for_integration(integration_id)

    deleted = await delete_integration(db, integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
    await _emit_audit(
        request,
        event_type="integration.delete",
        integration_id=integration_id,
        status="success",
    )


# ---------------------------------------------------------------------------
# Credentials (per integration)
# ---------------------------------------------------------------------------


def _get_vault(request: Request):
    """Get the vault from app.state or raise 503."""
    vault = getattr(request.app.state, "vault", None)
    if vault is None:
        raise HTTPException(
            status_code=503,
            detail="Credential vault not initialized. Set OPENSEC_CREDENTIAL_KEY.",
        )
    return vault


@router.get(
    "/settings/integrations/{integration_id}/credentials",
    response_model=list[CredentialInfo],
)
async def list_credentials(
    integration_id: str, request: Request, db: aiosqlite.Connection = Depends(get_db)
):
    """List credential key names for an integration (no values)."""
    integration = await get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    vault = _get_vault(request)
    keys = await vault.list_keys(integration_id)
    return [CredentialInfo(**k) for k in keys]


@router.post(
    "/settings/integrations/{integration_id}/credentials",
    response_model=CredentialInfo,
    status_code=201,
)
async def store_credential(
    integration_id: str,
    body: CredentialCreate,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Store an encrypted credential for an integration."""
    integration = await get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    vault = _get_vault(request)
    try:
        await vault.store(integration_id, body.key_name, body.value)
    except CredentialKeyError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await _emit_audit(
        request,
        event_type="credential.store",
        integration_id=integration_id,
        provider_name=integration.provider_name,
        status="success",
    )

    # Return info (no value).
    keys = await vault.list_keys(integration_id)
    for k in keys:
        if k["key_name"] == body.key_name:
            return CredentialInfo(**k)
    # Fallback (should not happen).
    return CredentialInfo(key_name=body.key_name, created_at="")


@router.delete(
    "/settings/integrations/{integration_id}/credentials/{key_name}",
    status_code=204,
)
async def delete_credential(
    integration_id: str, key_name: str, request: Request, db=Depends(get_db)
):
    """Delete a single credential."""
    vault = _get_vault(request)
    deleted = await vault.delete(integration_id, key_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")
    await _emit_audit(
        request,
        event_type="credential.delete",
        integration_id=integration_id,
        status="success",
    )


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------


@router.post(
    "/settings/integrations/{integration_id}/test",
    response_model=TestConnectionResult,
)
async def test_connection(
    integration_id: str, request: Request, db: aiosqlite.Connection = Depends(get_db)
):
    """Test an integration's credentials by verifying they can be decrypted."""
    integration = await get_integration(db, integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    vault = _get_vault(request)

    try:
        creds = await vault.get_credentials_for_workspace(integration_id)
    except CredentialKeyError as exc:
        result = TestConnectionResult(success=False, message=f"Vault error: {exc}")
        await _emit_audit(
            request,
            event_type="integration.test",
            integration_id=integration_id,
            provider_name=integration.provider_name,
            status="error",
            error_message=str(exc),
        )
        return result

    if not creds:
        result = TestConnectionResult(
            success=False, message="No credentials configured for this integration."
        )
        await _emit_audit(
            request,
            event_type="integration.test",
            integration_id=integration_id,
            provider_name=integration.provider_name,
            status="error",
            error_message="No credentials",
        )
        return result

    # Dispatch to a real connection tester if one exists for this provider.
    registry_id = integration.provider_name.lower().replace(" ", "-")
    result = await run_connection_test(registry_id, creds)

    if result is None:
        # No tester registered — fall back to "credentials decrypted" check.
        result = TestConnectionResult(
            success=True,
            message=f"Credentials valid ({len(creds)} key(s) decrypted successfully).",
            details={"credential_keys": list(creds.keys())},
        )

    await _emit_audit(
        request,
        event_type="integration.test",
        integration_id=integration_id,
        provider_name=integration.provider_name,
        status="success" if result.success else "error",
        error_message=result.message if not result.success else None,
    )
    return result


# ---------------------------------------------------------------------------
# Integration health
# ---------------------------------------------------------------------------


def _get_health_monitor(request: Request) -> IntegrationHealthMonitor:
    """Build a health monitor from app.state components."""
    vault = _get_vault(request)
    audit_logger = getattr(request.app.state, "audit_logger", None)
    return IntegrationHealthMonitor(vault, audit_logger=audit_logger)


@router.get(
    "/settings/integrations/{integration_id}/health",
    response_model=IntegrationHealthStatus,
)
async def check_integration_health(
    integration_id: str,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Run a health check for a single integration."""
    monitor = _get_health_monitor(request)
    health = await monitor.check_health(db, integration_id)
    if health is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return health


@router.get(
    "/settings/integrations/health",
    response_model=list[IntegrationHealthStatus],
)
async def check_all_integrations_health(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Run health checks for all enabled integrations."""
    monitor = _get_health_monitor(request)
    return await monitor.check_all(db)
