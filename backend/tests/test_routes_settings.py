"""Tests for the settings API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_model(db_client):
    """GET /api/settings/model returns current model config."""
    with patch(
        "opensec.engine.config_manager.opencode_client"
    ) as mock_client:
        mock_client.get_config = AsyncMock(
            return_value={"model": "openai/gpt-4.1-nano"}
        )
        resp = await db_client.get("/api/settings/model")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_full_id"] == "openai/gpt-4.1-nano"
        assert data["provider"] == "openai"
        assert data["model_id"] == "gpt-4.1-nano"


@pytest.mark.asyncio
async def test_update_model(db_client, tmp_path):
    """PUT /api/settings/model updates the model."""
    with (
        patch(
            "opensec.engine.config_manager.opencode_client"
        ) as mock_client,
        patch(
            "opensec.engine.config_manager.settings"
        ) as mock_settings,
    ):
        mock_client.update_config = AsyncMock(return_value={})
        mock_client.get_config = AsyncMock(
            return_value={"model": "anthropic/claude-sonnet-4-20250514"}
        )
        mock_settings.write_opencode_config = lambda m: None
        mock_settings.opencode_model = "anthropic/claude-sonnet-4-20250514"

        resp = await db_client.put(
            "/api/settings/model",
            json={"model_full_id": "anthropic/claude-sonnet-4-20250514"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_full_id"] == "anthropic/claude-sonnet-4-20250514"


@pytest.mark.asyncio
async def test_update_model_invalid_format(db_client):
    """PUT /api/settings/model rejects invalid model format."""
    resp = await db_client.put(
        "/api/settings/model",
        json={"model_full_id": "no-slash-here"},
    )
    assert resp.status_code == 400
    assert "provider/model-id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_providers(db_client):
    """GET /api/settings/providers returns provider list."""
    with patch(
        "opensec.engine.config_manager.opencode_client"
    ) as mock_client:
        mock_client.list_providers = AsyncMock(
            return_value={
                "all": [
                    {"id": "openai", "name": "OpenAI", "env": ["OPENAI_API_KEY"], "models": {}},
                ]
            }
        )
        resp = await db_client.get("/api/settings/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "openai"


@pytest.mark.asyncio
async def test_set_api_key(db_client):
    """PUT /api/settings/api-keys/{provider} stores a masked key."""
    with patch(
        "opensec.engine.config_manager.opencode_client"
    ) as mock_client:
        mock_client.set_auth = AsyncMock(return_value=True)

        resp = await db_client.put(
            "/api/settings/api-keys/openai",
            json={"provider": "openai", "key": "sk-test1234567890ab"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["key_masked"] == "sk-...90ab"
        assert data["has_credentials"] is True
        # Full key must NOT be in response
        assert "sk-test1234567890ab" not in str(data)


@pytest.mark.asyncio
async def test_list_api_keys_masked(db_client):
    """GET /api/settings/api-keys returns only masked keys."""
    with patch(
        "opensec.engine.config_manager.opencode_client"
    ) as mock_client:
        mock_client.set_auth = AsyncMock(return_value=True)
        mock_client.get_provider_auth = AsyncMock(return_value={})

        # Store a key first
        await db_client.put(
            "/api/settings/api-keys/openai",
            json={"provider": "openai", "key": "sk-secret-key-here1"},
        )

        resp = await db_client.get("/api/settings/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["key_masked"] == "sk-...ere1"
        # Full key must NOT be in response
        assert "sk-secret-key-here1" not in str(data)


@pytest.mark.asyncio
async def test_delete_api_key(db_client):
    """DELETE /api/settings/api-keys/{provider} removes the key."""
    with patch(
        "opensec.engine.config_manager.opencode_client"
    ) as mock_client:
        mock_client.set_auth = AsyncMock(return_value=True)
        mock_client.get_provider_auth = AsyncMock(return_value={})

        # Store then delete
        await db_client.put(
            "/api/settings/api-keys/openai",
            json={"provider": "openai", "key": "sk-to-delete-12345"},
        )
        resp = await db_client.delete("/api/settings/api-keys/openai")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await db_client.get("/api/settings/api-keys")
        assert resp.json() == []


@pytest.mark.asyncio
async def test_delete_api_key_not_found(db_client):
    """DELETE /api/settings/api-keys/{provider} returns 404 for missing key."""
    resp = await db_client.delete("/api/settings/api-keys/nonexistent")
    assert resp.status_code == 404


# --- Integrations ---


@pytest.mark.asyncio
async def test_integrations_crud(db_client):
    """Full CRUD lifecycle for integrations."""
    # Create
    resp = await db_client.post(
        "/api/settings/integrations",
        json={"adapter_type": "finding_source", "provider_name": "Snyk"},
    )
    assert resp.status_code == 201
    integration = resp.json()
    assert integration["adapter_type"] == "finding_source"
    assert integration["provider_name"] == "Snyk"
    assert integration["enabled"] is True
    integration_id = integration["id"]

    # List
    resp = await db_client.get("/api/settings/integrations")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Update
    resp = await db_client.put(
        f"/api/settings/integrations/{integration_id}",
        json={"enabled": False},
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Delete
    resp = await db_client.delete(f"/api/settings/integrations/{integration_id}")
    assert resp.status_code == 204

    # Verify deleted
    resp = await db_client.get("/api/settings/integrations")
    assert resp.json() == []
