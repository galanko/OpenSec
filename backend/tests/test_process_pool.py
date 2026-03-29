"""Tests for Layer 3: WorkspaceProcessPool, PortAllocator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from opensec.engine.pool import PortAllocator, WorkspaceProcess, WorkspaceProcessPool

# ---------------------------------------------------------------------------
# PortAllocator
# ---------------------------------------------------------------------------


def test_allocate_returns_first_port():
    pa = PortAllocator(start=5000, end=5009)
    assert pa.allocate() == 5000


def test_allocate_sequential():
    pa = PortAllocator(start=5000, end=5009)
    assert pa.allocate() == 5000
    assert pa.allocate() == 5001
    assert pa.allocate() == 5002


def test_release_makes_port_available():
    pa = PortAllocator(start=5000, end=5009)
    port = pa.allocate()
    pa.release(port)
    assert pa.allocate() == port


def test_allocate_exhausted():
    pa = PortAllocator(start=5000, end=5002)
    pa.allocate()
    pa.allocate()
    pa.allocate()
    with pytest.raises(RuntimeError, match="No free ports"):
        pa.allocate()


def test_available_count():
    pa = PortAllocator(start=5000, end=5004)
    assert pa.available == 5
    pa.allocate()
    assert pa.available == 4
    pa.allocate()
    pa.release(5000)
    assert pa.available == 4


# ---------------------------------------------------------------------------
# WorkspaceProcess
# ---------------------------------------------------------------------------


def test_workspace_process_idle_seconds():
    wp = WorkspaceProcess(
        workspace_id="ws-1",
        workspace_dir=Path("/tmp/ws-1"),
        port=5000,
    )
    assert wp.idle_seconds >= 0


def test_workspace_process_touch():
    wp = WorkspaceProcess(
        workspace_id="ws-1",
        workspace_dir=Path("/tmp/ws-1"),
        port=5000,
    )
    import time

    time.sleep(0.05)
    idle_before = wp.idle_seconds
    wp.touch()
    idle_after = wp.idle_seconds
    assert idle_after < idle_before


def test_workspace_process_is_running():
    wp = WorkspaceProcess(
        workspace_id="ws-1",
        workspace_dir=Path("/tmp/ws-1"),
        port=5000,
    )
    assert wp.is_running is False

    mock_proc = MagicMock()
    mock_proc.returncode = None
    wp.process = mock_proc
    assert wp.is_running is True

    mock_proc.returncode = 0
    assert wp.is_running is False


# ---------------------------------------------------------------------------
# WorkspaceProcessPool (mocked subprocess + httpx)
# ---------------------------------------------------------------------------


def _make_mock_subprocess():
    """Create a mock asyncio subprocess."""
    proc = AsyncMock()
    proc.returncode = None
    proc.terminate = MagicMock()
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    proc.stderr = None
    proc.stdout = None
    return proc


def _make_mock_httpx_healthy():
    """Create a mock httpx context manager that returns 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


@pytest.fixture
def pool():
    """Process pool with a small port range for testing."""
    return WorkspaceProcessPool(
        port_allocator=PortAllocator(start=5100, end=5109),
        host="127.0.0.1",
    )


async def test_start_allocates_port_and_starts_process(pool: WorkspaceProcessPool):
    mock_proc = _make_mock_subprocess()
    mock_httpx = _make_mock_httpx_healthy()

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ) as mock_exec,
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        client = await pool.start("ws-1", Path("/tmp/ws-1"))

    assert client is not None
    assert client.base_url == "http://127.0.0.1:5100"

    # Verify subprocess was called with correct cwd
    call_kwargs = mock_exec.call_args
    assert str(call_kwargs.kwargs.get("cwd")) == "/tmp/ws-1"


async def test_get_or_start_returns_existing(pool: WorkspaceProcessPool):
    mock_proc = _make_mock_subprocess()
    mock_httpx = _make_mock_httpx_healthy()

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ) as mock_exec,
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        client1 = await pool.get_or_start("ws-1", Path("/tmp/ws-1"))
        client2 = await pool.get_or_start("ws-1", Path("/tmp/ws-1"))

    assert client1 is client2
    # Only one subprocess created
    assert mock_exec.call_count == 1


async def test_stop_terminates_and_releases_port(pool: WorkspaceProcessPool):
    mock_proc = _make_mock_subprocess()
    mock_httpx = _make_mock_httpx_healthy()

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ),
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        await pool.start("ws-1", Path("/tmp/ws-1"))

    assert pool._ports.available == 9  # 1 of 10 used

    mock_proc.returncode = None  # still running
    await pool.stop("ws-1")

    mock_proc.terminate.assert_called_once()
    assert pool._ports.available == 10  # port released
    assert await pool.get("ws-1") is None


async def test_stop_all(pool: WorkspaceProcessPool):
    mock_httpx = _make_mock_httpx_healthy()

    procs = [_make_mock_subprocess() for _ in range(3)]

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=procs),
        ),
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        await pool.start("ws-1", Path("/tmp/ws-1"))
        await pool.start("ws-2", Path("/tmp/ws-2"))
        await pool.start("ws-3", Path("/tmp/ws-3"))

    assert pool._ports.available == 7

    for p in procs:
        p.returncode = None

    await pool.stop_all()

    assert pool._ports.available == 10
    assert len(pool._processes) == 0


async def test_stop_idle(pool: WorkspaceProcessPool):
    mock_httpx = _make_mock_httpx_healthy()
    procs = [_make_mock_subprocess() for _ in range(2)]

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=procs),
        ),
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        await pool.start("ws-old", Path("/tmp/ws-old"))
        await pool.start("ws-new", Path("/tmp/ws-new"))

    # Make ws-old appear idle by manipulating last_activity
    import time

    pool._processes["ws-old"].last_activity = time.monotonic() - 999

    for p in procs:
        p.returncode = None

    from datetime import timedelta

    stopped = await pool.stop_idle(timedelta(seconds=10))

    assert "ws-old" in stopped
    assert "ws-new" not in stopped
    assert len(pool._processes) == 1


async def test_start_failure_releases_port(pool: WorkspaceProcessPool):
    """If health check fails, port must be released."""
    mock_proc = _make_mock_subprocess()
    # Simulate process dying immediately
    mock_proc.returncode = 1
    mock_proc.stderr = AsyncMock()
    mock_proc.stderr.read = AsyncMock(return_value=b"startup failed")

    import httpx as httpx_mod

    mock_httpx = AsyncMock()
    mock_httpx.get = AsyncMock(
        side_effect=httpx_mod.ConnectError("connection refused")
    )
    mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
    mock_httpx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ),
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
        pytest.raises(RuntimeError, match="exited with code 1"),
    ):
        await pool.start("ws-fail", Path("/tmp/ws-fail"))

    # Port must be released even though start failed
    assert pool._ports.available == 10


async def test_status(pool: WorkspaceProcessPool):
    mock_proc = _make_mock_subprocess()
    mock_httpx = _make_mock_httpx_healthy()

    with (
        patch(
            "opensec.engine.pool.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ),
        patch("opensec.engine.pool.httpx.AsyncClient", return_value=mock_httpx),
    ):
        await pool.start("ws-1", Path("/tmp/ws-1"))

    status = pool.status()
    assert status["active_processes"] == 1
    assert status["available_ports"] == 9
    assert "ws-1" in status["workspaces"]
    assert status["workspaces"]["ws-1"]["port"] == 5100
