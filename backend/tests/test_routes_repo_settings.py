"""Tests for repository settings endpoints (T2.5 + T2.6)."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from opensec.main import app

if TYPE_CHECKING:
    from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_VAULT_KEY = b"0" * 32  # 32-byte AES key for tests


@pytest.fixture
async def vault_client(db_client: AsyncClient):
    """db_client with a real vault attached for credential storage."""
    from opensec.db.connection import get_db
    from opensec.integrations.vault import CredentialVault

    db = await anext(get_db())
    vault = CredentialVault(db, key=TEST_VAULT_KEY)
    app.state.vault = vault
    yield db_client
    app.state.vault = None


# ---------------------------------------------------------------------------
# GET /api/settings/repo
# ---------------------------------------------------------------------------


async def test_get_repo_settings_empty(db_client: AsyncClient):
    """GET returns empty state when nothing configured."""
    resp = await db_client.get("/api/settings/repo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] is None
    assert data["has_token"] is False


async def test_get_repo_settings_vault_none(db_client: AsyncClient):
    """GET handles vault=None gracefully (has_token always false)."""
    # db_client fixture already has vault=None
    resp = await db_client.get("/api/settings/repo")
    assert resp.status_code == 200
    assert resp.json()["has_token"] is False


# ---------------------------------------------------------------------------
# PUT /api/settings/repo
# ---------------------------------------------------------------------------


async def test_put_repo_url(db_client: AsyncClient):
    """PUT with url stores it and returns updated response."""
    resp = await db_client.put(
        "/api/settings/repo",
        json={"url": "https://github.com/org/repo"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] == "https://github.com/org/repo"
    assert data["has_token"] is False


async def test_put_repo_token(vault_client: AsyncClient):
    """PUT with token stores it (encrypted) and has_token becomes true."""
    resp = await vault_client.put(
        "/api/settings/repo",
        json={"token": "ghp_testtoken123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_token"] is True


async def test_put_repo_clear_token(vault_client: AsyncClient):
    """PUT with empty token clears it."""
    # Store first
    await vault_client.put("/api/settings/repo", json={"token": "ghp_temp"})
    # Clear
    resp = await vault_client.put("/api/settings/repo", json={"token": ""})
    assert resp.status_code == 200
    assert resp.json()["has_token"] is False


async def test_put_repo_token_without_vault(db_client: AsyncClient):
    """PUT with token when vault not available returns 503."""
    resp = await db_client.put(
        "/api/settings/repo",
        json={"token": "ghp_test"},
    )
    assert resp.status_code == 503


async def test_get_repo_settings_after_store(vault_client: AsyncClient):
    """GET returns correct values after storing both url and token."""
    await vault_client.put(
        "/api/settings/repo",
        json={"url": "https://github.com/org/repo", "token": "ghp_full"},
    )
    resp = await vault_client.get("/api/settings/repo")
    data = resp.json()
    assert data["url"] == "https://github.com/org/repo"
    assert data["has_token"] is True


# ---------------------------------------------------------------------------
# POST /api/settings/repo/test
# ---------------------------------------------------------------------------


async def test_repo_test_connection_success(db_client: AsyncClient):
    """POST test endpoint with mocked git success returns success result."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(
        return_value=(b"abc123\trefs/heads/main\ndef456\trefs/heads/dev\n", b"")
    )
    mock_proc.returncode = 0

    with patch(
        "opensec.api.routes.settings.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=mock_proc),
    ):
        resp = await db_client.post(
            "/api/settings/repo/test",
            json={"url": "https://github.com/org/repo", "token": "ghp_test"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "2" in data["message"]  # 2 branches found


async def test_repo_test_connection_failure(db_client: AsyncClient):
    """POST test with git failure returns error with sanitized message."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(
        return_value=(b"", b"fatal: repository not found with ghp_secret")
    )
    mock_proc.returncode = 128

    with patch(
        "opensec.api.routes.settings.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=mock_proc),
    ):
        resp = await db_client.post(
            "/api/settings/repo/test",
            json={"url": "https://github.com/org/repo", "token": "ghp_secret"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    # Token must be sanitized from error message
    assert "ghp_secret" not in data["message"]
    assert "***" in data["message"]


async def test_repo_test_invalid_url(db_client: AsyncClient):
    """POST test with non-HTTPS URL returns error."""
    resp = await db_client.post(
        "/api/settings/repo/test",
        json={"url": "ssh://git@github.com/org/repo", "token": "ghp_test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "https" in data["message"].lower()
