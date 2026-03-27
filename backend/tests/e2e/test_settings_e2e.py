"""E2E tests for Settings endpoints against a real OpenCode server.

Requires:
  - OpenCode binary installed
  - OPENAI_API_KEY (or another provider key) set in the environment

Skipped automatically if OpenCode binary or API key is missing.
"""

from __future__ import annotations


def test_get_providers(app_client):
    """GET /api/settings/providers returns a non-empty provider list."""
    resp = app_client.get("/api/settings/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert isinstance(providers, list)
    assert len(providers) > 0
    provider = providers[0]
    assert "id" in provider
    assert "name" in provider


def test_get_model(app_client):
    """GET /api/settings/model returns the current model."""
    resp = app_client.get("/api/settings/model")
    assert resp.status_code == 200
    data = resp.json()
    assert "model_full_id" in data
    assert "/" in data["model_full_id"]


def test_update_model_and_verify(app_client):
    """PUT /api/settings/model changes the model at runtime."""
    # Get current model
    resp = app_client.get("/api/settings/model")
    original_model = resp.json()["model_full_id"]

    # Change to a different model (same provider to avoid auth issues)
    new_model = "openai/gpt-4.1-mini" if "nano" in original_model else "openai/gpt-4.1-nano"

    resp = app_client.put(
        "/api/settings/model",
        json={"model_full_id": new_model},
    )
    assert resp.status_code == 200
    assert resp.json()["model_full_id"] == new_model

    # Verify via health endpoint
    resp = app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["model"] == new_model

    # Restore original model
    app_client.put(
        "/api/settings/model",
        json={"model_full_id": original_model},
    )


def test_update_model_invalid_format(app_client):
    """PUT /api/settings/model rejects models without provider prefix."""
    resp = app_client.put(
        "/api/settings/model",
        json={"model_full_id": "gpt-4"},
    )
    assert resp.status_code == 400


def test_api_key_roundtrip(app_client):
    """Set and retrieve an API key, verify it's masked."""
    # Set a test key (using a dummy provider to avoid conflicts)
    resp = app_client.put(
        "/api/settings/api-keys/test-provider",
        json={"provider": "test-provider", "key": "sk-e2e-test-key-12345"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key_masked"] == "sk-...2345"

    # List keys and verify masking
    resp = app_client.get("/api/settings/api-keys")
    assert resp.status_code == 200
    keys = resp.json()
    test_keys = [k for k in keys if k["provider"] == "test-provider"]
    assert len(test_keys) == 1
    assert "sk-e2e-test-key-12345" not in str(test_keys)

    # Clean up
    resp = app_client.delete("/api/settings/api-keys/test-provider")
    assert resp.status_code == 204
