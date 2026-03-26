"""Repository functions for the SidebarState entity."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import SidebarState, SidebarStateUpdate

if TYPE_CHECKING:
    import aiosqlite

_JSON_FIELDS = (
    "summary",
    "evidence",
    "owner",
    "plan",
    "definition_of_done",
    "linked_ticket",
    "validation",
    "similar_cases",
)


def _row_to_sidebar(row: aiosqlite.Row) -> SidebarState:
    return SidebarState(
        workspace_id=row["workspace_id"],
        summary=json.loads(row["summary"]) if row["summary"] else None,
        evidence=json.loads(row["evidence"]) if row["evidence"] else None,
        owner=json.loads(row["owner"]) if row["owner"] else None,
        plan=json.loads(row["plan"]) if row["plan"] else None,
        definition_of_done=(
            json.loads(row["definition_of_done"]) if row["definition_of_done"] else None
        ),
        linked_ticket=json.loads(row["linked_ticket"]) if row["linked_ticket"] else None,
        validation=json.loads(row["validation"]) if row["validation"] else None,
        similar_cases=json.loads(row["similar_cases"]) if row["similar_cases"] else None,
        updated_at=row["updated_at"],
    )


async def upsert_sidebar(
    db: aiosqlite.Connection, workspace_id: str, data: SidebarStateUpdate
) -> SidebarState:
    now = datetime.now(UTC).isoformat()
    values = {k: json.dumps(v) if v is not None else None for k, v in data.model_dump().items()}
    await db.execute(
        """
        INSERT INTO sidebar_state
            (workspace_id, summary, evidence, owner, plan,
             definition_of_done, linked_ticket, validation, similar_cases, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_id) DO UPDATE SET
            summary = excluded.summary,
            evidence = excluded.evidence,
            owner = excluded.owner,
            plan = excluded.plan,
            definition_of_done = excluded.definition_of_done,
            linked_ticket = excluded.linked_ticket,
            validation = excluded.validation,
            similar_cases = excluded.similar_cases,
            updated_at = excluded.updated_at
        """,
        (
            workspace_id,
            values["summary"],
            values["evidence"],
            values["owner"],
            values["plan"],
            values["definition_of_done"],
            values["linked_ticket"],
            values["validation"],
            values["similar_cases"],
            now,
        ),
    )
    await db.commit()
    return await get_sidebar(db, workspace_id)  # type: ignore[return-value]


async def get_sidebar(db: aiosqlite.Connection, workspace_id: str) -> SidebarState | None:
    cursor = await db.execute(
        "SELECT * FROM sidebar_state WHERE workspace_id = ?", (workspace_id,)
    )
    row = await cursor.fetchone()
    return _row_to_sidebar(row) if row else None
