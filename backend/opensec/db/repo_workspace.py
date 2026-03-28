"""Repository functions for the Workspace entity."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import Workspace, WorkspaceCreate, WorkspaceUpdate

if TYPE_CHECKING:
    import aiosqlite


def _row_to_workspace(row: aiosqlite.Row) -> Workspace:
    return Workspace(
        id=row["id"],
        finding_id=row["finding_id"],
        state=row["state"],
        current_focus=row["current_focus"],
        active_plan_version=row["active_plan_version"],
        linked_ticket_id=row["linked_ticket_id"],
        validation_state=row["validation_state"],
        workspace_dir=row["workspace_dir"],
        context_version=row["context_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_workspace(db: aiosqlite.Connection, data: WorkspaceCreate) -> Workspace:
    workspace_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        INSERT INTO workspace
            (id, finding_id, state, current_focus, active_plan_version,
             linked_ticket_id, validation_state, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            workspace_id,
            data.finding_id,
            data.state,
            data.current_focus,
            None,
            None,
            None,
            now,
            now,
        ),
    )
    await db.commit()
    return await get_workspace(db, workspace_id)  # type: ignore[return-value]


async def get_workspace(db: aiosqlite.Connection, workspace_id: str) -> Workspace | None:
    cursor = await db.execute("SELECT * FROM workspace WHERE id = ?", (workspace_id,))
    row = await cursor.fetchone()
    return _row_to_workspace(row) if row else None


async def list_workspaces(
    db: aiosqlite.Connection,
    *,
    state: str | None = None,
    finding_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Workspace]:
    conditions: list[str] = []
    params: list[str | int] = []
    if state:
        conditions.append("state = ?")
        params.append(state)
    if finding_id:
        conditions.append("finding_id = ?")
        params.append(finding_id)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])
    cursor = await db.execute(
        f"SELECT * FROM workspace {where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",  # noqa: S608
        params,
    )
    return [_row_to_workspace(row) for row in await cursor.fetchall()]


async def update_workspace(
    db: aiosqlite.Connection, workspace_id: str, data: WorkspaceUpdate
) -> Workspace | None:
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await get_workspace(db, workspace_id)

    fields["updated_at"] = datetime.now(UTC).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = [*fields.values(), workspace_id]

    await db.execute(f"UPDATE workspace SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
    return await get_workspace(db, workspace_id)


async def delete_workspace(db: aiosqlite.Connection, workspace_id: str) -> bool:
    cursor = await db.execute("DELETE FROM workspace WHERE id = ?", (workspace_id,))
    await db.commit()
    return cursor.rowcount > 0


async def update_workspace_dir(
    db: aiosqlite.Connection, workspace_id: str, workspace_dir: str
) -> None:
    """Set the workspace_dir path. Called once after directory creation."""
    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE workspace SET workspace_dir = ?, updated_at = ? WHERE id = ?",
        (workspace_dir, now, workspace_id),
    )
    await db.commit()


async def increment_context_version(
    db: aiosqlite.Connection, workspace_id: str
) -> int:
    """Atomically increment context_version. Returns the new version."""
    now = datetime.now(UTC).isoformat()
    await db.execute(
        "UPDATE workspace SET context_version = context_version + 1, updated_at = ? WHERE id = ?",
        (now, workspace_id),
    )
    await db.commit()
    cursor = await db.execute(
        "SELECT context_version FROM workspace WHERE id = ?", (workspace_id,)
    )
    row = await cursor.fetchone()
    return row["context_version"] if row else 0
