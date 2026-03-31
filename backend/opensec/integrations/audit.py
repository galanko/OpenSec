"""Integration audit logger with hash-chain tamper evidence (ADR-0017).

Events are queued in-process and written asynchronously by a background task.
If the queue is full, events fall back to synchronous writes (never dropped).

Every event includes ``event_hash`` (SHA-256 of canonical event data) and
``prev_hash`` (the ``event_hash`` of the preceding event), forming a
verifiable chain. Any modification to historical events breaks the chain.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from opensec.db import repo_audit

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """Structured audit event for integration actions."""

    event_type: str  # e.g. "integration.create", "credential.store", "mcp.tool_call"
    actor_type: str = "user"  # "user", "agent", "system"
    actor_id: str | None = None
    workspace_id: str | None = None
    integration_id: str | None = None
    provider_name: str | None = None
    tool_name: str | None = None
    verb: str | None = None  # "collect", "enrich", "investigate", "update"
    action_tier: int = Field(default=0, ge=0, le=2)  # 0=read, 1=enrich, 2=mutate
    status: str = "success"  # "success", "error", "timeout", "denied"
    duration_ms: int | None = None
    parameters_hash: str | None = None  # SHA-256 of parameters, never raw values
    error_message: str | None = None
    correlation_id: str | None = None


# ---------------------------------------------------------------------------
# Hash computation
# ---------------------------------------------------------------------------


def compute_event_hash(event_dict: dict[str, Any], prev_hash: str | None) -> str:
    """SHA-256 of canonical event JSON concatenated with prev_hash."""
    canonical = json.dumps(event_dict, sort_keys=True, default=str)
    payload = canonical + (prev_hash or "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def hash_parameters(params: dict[str, Any] | str | None) -> str | None:
    """Hash parameters for audit storage. Never store raw values."""
    if params is None:
        return None
    if isinstance(params, str):
        return hashlib.sha256(params.encode("utf-8")).hexdigest()
    canonical = json.dumps(params, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Async, non-blocking audit logger with hash-chain tamper evidence."""

    def __init__(self, db: aiosqlite.Connection, *, max_queue_size: int = 1000) -> None:
        self._db = db
        self._queue: asyncio.Queue[AuditEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._writer_task: asyncio.Task[None] | None = None
        self._running = False
        self._last_hash: str | None = None  # In-memory cache of latest hash

    async def start(self) -> None:
        """Start the background writer task."""
        if self._running:
            return
        # Seed the hash chain from the last stored event.
        self._last_hash = await repo_audit.get_last_event_hash(self._db)
        self._running = True
        self._writer_task = asyncio.create_task(self._writer_loop())
        logger.info("Audit logger started")

    async def stop(self) -> None:
        """Drain the queue and stop the writer."""
        if not self._running:
            return
        self._running = False
        # Drain remaining events.
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                await self._write_event(event)
            except asyncio.QueueEmpty:
                break
        if self._writer_task is not None:
            self._writer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._writer_task
            self._writer_task = None
        logger.info("Audit logger stopped")

    async def log(self, event: AuditEvent) -> None:
        """Log an audit event (non-blocking). Falls back to sync if queue is full."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Audit queue full — writing synchronously")
            await self._write_event(event)

    async def _writer_loop(self) -> None:
        """Background task that consumes events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._write_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error writing audit event")

    async def _write_event(self, event: AuditEvent) -> None:
        """Compute hash chain and persist event to the database."""
        now = datetime.now(UTC).isoformat()
        event_dict = event.model_dump()
        event_dict["timestamp"] = now

        event_hash = compute_event_hash(event_dict, self._last_hash)
        event_dict["prev_hash"] = self._last_hash
        event_dict["event_hash"] = event_hash

        await repo_audit.insert_audit_event(self._db, event_dict)
        self._last_hash = event_hash

    async def verify_chain(self, *, limit: int = 1000) -> tuple[bool, int]:
        """Verify hash-chain integrity. Returns (is_valid, events_checked)."""
        events = await repo_audit.get_events_for_verification(self._db, limit=limit)
        if not events:
            return True, 0

        prev_hash: str | None = None
        for i, row in enumerate(events):
            # Reconstruct event dict (exclude DB-only fields)
            event_dict = {
                "event_type": row["event_type"],
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "workspace_id": row["workspace_id"],
                "integration_id": row["integration_id"],
                "provider_name": row["provider_name"],
                "tool_name": row["tool_name"],
                "verb": row["verb"],
                "action_tier": row["action_tier"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "parameters_hash": row["parameters_hash"],
                "error_message": row["error_message"],
                "correlation_id": row["correlation_id"],
                "timestamp": row["timestamp"],
            }

            expected_hash = compute_event_hash(event_dict, prev_hash)
            if row["event_hash"] != expected_hash:
                logger.warning(
                    "Audit chain broken at event id=%s (expected %s, got %s)",
                    row["id"],
                    expected_hash,
                    row["event_hash"],
                )
                return False, i

            # Verify prev_hash linkage
            if row["prev_hash"] != prev_hash:
                logger.warning(
                    "Audit chain prev_hash mismatch at event id=%s", row["id"]
                )
                return False, i

            prev_hash = row["event_hash"]

        return True, len(events)
