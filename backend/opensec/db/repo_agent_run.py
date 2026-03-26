"""Repository functions for the AgentRun entity."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import AgentRun, AgentRunCreate, AgentRunUpdate

if TYPE_CHECKING:
    import aiosqlite

_JSON_FIELDS = {"input_json", "evidence_json", "structured_output"}


def _row_to_agent_run(row: aiosqlite.Row) -> AgentRun:
    return AgentRun(
        id=row["id"],
        workspace_id=row["workspace_id"],
        agent_type=row["agent_type"],
        status=row["status"],
        input_json=json.loads(row["input_json"]) if row["input_json"] else None,
        summary_markdown=row["summary_markdown"],
        confidence=row["confidence"],
        evidence_json=json.loads(row["evidence_json"]) if row["evidence_json"] else None,
        structured_output=(
            json.loads(row["structured_output"]) if row["structured_output"] else None
        ),
        next_action_hint=row["next_action_hint"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


async def create_agent_run(
    db: aiosqlite.Connection, workspace_id: str, data: AgentRunCreate
) -> AgentRun:
    run_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    started = now if data.status == "running" else None
    await db.execute(
        """
        INSERT INTO agent_run
            (id, workspace_id, agent_type, status, input_json, started_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            workspace_id,
            data.agent_type,
            data.status,
            json.dumps(data.input_json) if data.input_json is not None else None,
            started,
        ),
    )
    await db.commit()
    return await get_agent_run(db, run_id)  # type: ignore[return-value]


async def get_agent_run(db: aiosqlite.Connection, run_id: str) -> AgentRun | None:
    cursor = await db.execute("SELECT * FROM agent_run WHERE id = ?", (run_id,))
    row = await cursor.fetchone()
    return _row_to_agent_run(row) if row else None


async def list_agent_runs(
    db: aiosqlite.Connection,
    workspace_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[AgentRun]:
    cursor = await db.execute(
        "SELECT * FROM agent_run WHERE workspace_id = ?"
        " ORDER BY started_at DESC NULLS LAST LIMIT ? OFFSET ?",
        (workspace_id, limit, offset),
    )
    return [_row_to_agent_run(row) for row in await cursor.fetchall()]


async def update_agent_run(
    db: aiosqlite.Connection, run_id: str, data: AgentRunUpdate
) -> AgentRun | None:
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await get_agent_run(db, run_id)

    now = datetime.now(UTC).isoformat()

    # Auto-set timestamps based on status transitions.
    if "status" in fields:
        if fields["status"] == "running":
            fields["started_at"] = now
        elif fields["status"] in ("completed", "failed", "cancelled"):
            fields["completed_at"] = now

    # Serialize JSON fields.
    for key in _JSON_FIELDS:
        if key in fields and fields[key] is not None:
            fields[key] = json.dumps(fields[key])

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = [*fields.values(), run_id]

    await db.execute(f"UPDATE agent_run SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
    return await get_agent_run(db, run_id)
