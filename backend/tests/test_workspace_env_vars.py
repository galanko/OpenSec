"""Tests for _resolve_repo_env_vars helper in workspace routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from opensec.api.routes.workspaces import _resolve_repo_env_vars
from opensec.models import AppSetting


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request with optional vault."""
    req = MagicMock()
    req.app.state.vault = None
    return req


@pytest.fixture
def mock_db():
    """Create a mock aiosqlite connection."""
    return AsyncMock()


async def test_resolve_both_url_and_token(mock_request, mock_db):
    """When both URL setting and token exist, return full dict."""
    from unittest.mock import patch

    vault = AsyncMock()
    vault.retrieve = AsyncMock(return_value="ghp_realtoken")
    mock_request.app.state.vault = vault

    setting = AppSetting(
        key="repo:url", value={"url": "https://github.com/org/repo"}, updated_at="2026-01-01",
    )

    with patch("opensec.api.routes.workspaces.get_setting", new=AsyncMock(return_value=setting)):
        result = await _resolve_repo_env_vars(mock_request, mock_db)

    assert result == {
        "OPENSEC_REPO_URL": "https://github.com/org/repo",
        "GH_TOKEN": "ghp_realtoken",
    }


async def test_resolve_url_only(mock_request, mock_db):
    """When only URL is set (no token), return partial dict."""
    from unittest.mock import patch

    setting = AppSetting(
        key="repo:url", value={"url": "https://github.com/org/repo"}, updated_at="2026-01-01",
    )

    with patch("opensec.api.routes.workspaces.get_setting", new=AsyncMock(return_value=setting)):
        result = await _resolve_repo_env_vars(mock_request, mock_db)

    assert result == {"OPENSEC_REPO_URL": "https://github.com/org/repo"}
    assert "GH_TOKEN" not in result


async def test_resolve_neither(mock_request, mock_db):
    """When nothing configured, return empty dict."""
    from unittest.mock import patch

    with patch("opensec.api.routes.workspaces.get_setting", new=AsyncMock(return_value=None)):
        result = await _resolve_repo_env_vars(mock_request, mock_db)

    assert result == {}


async def test_resolve_vault_none(mock_request, mock_db):
    """When vault is None, only URL is returned (no GH_TOKEN)."""
    from unittest.mock import patch

    setting = AppSetting(
        key="repo:url", value={"url": "https://github.com/x/y"}, updated_at="2026-01-01",
    )
    mock_request.app.state.vault = None

    with patch("opensec.api.routes.workspaces.get_setting", new=AsyncMock(return_value=setting)):
        result = await _resolve_repo_env_vars(mock_request, mock_db)

    assert result == {"OPENSEC_REPO_URL": "https://github.com/x/y"}
    assert "GH_TOKEN" not in result
