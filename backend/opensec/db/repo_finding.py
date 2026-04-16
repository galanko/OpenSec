"""Repository functions for the Finding entity."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import Finding, FindingCreate, FindingUpdate

if TYPE_CHECKING:
    import aiosqlite


def _row_to_finding(row: aiosqlite.Row) -> Finding:
    return Finding(
        id=row["id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        title=row["title"],
        description=row["description"],
        plain_description=row["plain_description"],
        raw_severity=row["raw_severity"],
        normalized_priority=row["normalized_priority"],
        asset_id=row["asset_id"],
        asset_label=row["asset_label"],
        status=row["status"],
        likely_owner=row["likely_owner"],
        why_this_matters=row["why_this_matters"],
        raw_payload=json.loads(row["raw_payload"]) if row["raw_payload"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_finding(db: aiosqlite.Connection, data: FindingCreate) -> Finding:
    finding_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        INSERT INTO finding
            (id, source_type, source_id, title, description, plain_description,
             raw_severity, normalized_priority, asset_id, asset_label, status,
             likely_owner, why_this_matters, raw_payload, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            finding_id,
            data.source_type,
            data.source_id,
            data.title,
            data.description,
            data.plain_description,
            data.raw_severity,
            data.normalized_priority,
            data.asset_id,
            data.asset_label,
            data.status,
            data.likely_owner,
            data.why_this_matters,
            json.dumps(data.raw_payload) if data.raw_payload is not None else None,
            now,
            now,
        ),
    )
    await db.commit()
    return await get_finding(db, finding_id)  # type: ignore[return-value]


async def get_finding(db: aiosqlite.Connection, finding_id: str) -> Finding | None:
    cursor = await db.execute("SELECT * FROM finding WHERE id = ?", (finding_id,))
    row = await cursor.fetchone()
    return _row_to_finding(row) if row else None


async def list_findings(
    db: aiosqlite.Connection,
    *,
    status: str | None = None,
    has_workspace: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Finding]:
    conditions: list[str] = []
    params: list[str | int] = []

    if status:
        conditions.append("f.status = ?")
        params.append(status)

    if has_workspace is True:
        conditions.append(
            "EXISTS (SELECT 1 FROM workspace w WHERE w.finding_id = f.id)"
        )
    elif has_workspace is False:
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM workspace w WHERE w.finding_id = f.id)"
        )

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.extend([limit, offset])
    cursor = await db.execute(
        f"SELECT f.* FROM finding f {where}"  # noqa: S608
        " ORDER BY f.updated_at DESC LIMIT ? OFFSET ?",
        params,
    )
    return [_row_to_finding(row) for row in await cursor.fetchall()]


async def update_finding(
    db: aiosqlite.Connection, finding_id: str, data: FindingUpdate
) -> Finding | None:
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await get_finding(db, finding_id)

    # Serialize JSON field if present.
    if "raw_payload" in fields and fields["raw_payload"] is not None:
        fields["raw_payload"] = json.dumps(fields["raw_payload"])

    fields["updated_at"] = datetime.now(UTC).isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = [*fields.values(), finding_id]

    await db.execute(f"UPDATE finding SET {set_clause} WHERE id = ?", values)  # noqa: S608
    await db.commit()
    return await get_finding(db, finding_id)


async def delete_finding(db: aiosqlite.Connection, finding_id: str) -> bool:
    cursor = await db.execute("DELETE FROM finding WHERE id = ?", (finding_id,))
    await db.commit()
    return cursor.rowcount > 0
