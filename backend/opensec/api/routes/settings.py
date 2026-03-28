"""Settings API endpoints — model, API keys, integrations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from opensec.db.connection import get_db
from opensec.db.repo_integration import (
    create_integration,
    delete_integration,
    list_integrations,
    update_integration,
)
from opensec.engine.config_manager import config_manager
from opensec.models import (
    ApiKeyCreate,
    IntegrationConfig,
    IntegrationConfigCreate,
    IntegrationConfigUpdate,
    ModelConfig,
    ModelUpdateRequest,
)

router = APIRouter(tags=["settings"])

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
# Integrations
# ---------------------------------------------------------------------------


@router.get("/settings/integrations", response_model=list[IntegrationConfig])
async def list_integrations_endpoint(db=Depends(get_db)):
    return await list_integrations(db)


@router.post("/settings/integrations", response_model=IntegrationConfig, status_code=201)
async def create_integration_endpoint(body: IntegrationConfigCreate, db=Depends(get_db)):
    return await create_integration(db, body)


@router.put("/settings/integrations/{integration_id}", response_model=IntegrationConfig)
async def update_integration_endpoint(
    integration_id: str, body: IntegrationConfigUpdate, db=Depends(get_db)
):
    result = await update_integration(db, integration_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Integration not found")
    return result


@router.delete("/settings/integrations/{integration_id}", status_code=204)
async def delete_integration_endpoint(integration_id: str, db=Depends(get_db)):
    deleted = await delete_integration(db, integration_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Integration not found")
