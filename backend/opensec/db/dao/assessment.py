"""DAO for the ``assessment`` table (IMPL-0002 Milestone A2).

The assessment row is the event record for one scan run. ``criteria_snapshot`` is
stored as a JSON TEXT column and deserialized via the ``CriteriaSnapshot`` model.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import (
    Assessment,
    AssessmentCreate,
    AssessmentUpdate,
    CriteriaSnapshot,
    Grade,
)

if TYPE_CHECKING:
    import aiosqlite


def _row_to_assessment(row: aiosqlite.Row) -> Assessment:
    criteria_json = row["criteria_snapshot"]
    criteria = (
        CriteriaSnapshot.model_validate(json.loads(criteria_json)) if criteria_json else None
    )
    return Assessment(
        id=row["id"],
        repo_url=row["repo_url"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        status=row["status"],
        grade=row["grade"],
        criteria_snapshot=criteria,
    )


async def create_assessment(db: aiosqlite.Connection, data: AssessmentCreate) -> Assessment:
    assessment_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        INSERT INTO assessment
            (id, repo_url, started_at, completed_at, status, grade, criteria_snapshot)
        VALUES (?, ?, ?, NULL, 'pending', NULL, NULL)
        """,
        (assessment_id, data.repo_url, now),
    )
    await db.commit()
    fetched = await get_assessment(db, assessment_id)
    assert fetched is not None  # just inserted
    return fetched


async def get_assessment(db: aiosqlite.Connection, assessment_id: str) -> Assessment | None:
    cursor = await db.execute("SELECT * FROM assessment WHERE id = ?", (assessment_id,))
    row = await cursor.fetchone()
    return _row_to_assessment(row) if row else None


async def get_latest_assessment(db: aiosqlite.Connection) -> Assessment | None:
    cursor = await db.execute(
        "SELECT * FROM assessment ORDER BY started_at DESC, id DESC LIMIT 1"
    )
    row = await cursor.fetchone()
    return _row_to_assessment(row) if row else None


async def update_assessment(
    db: aiosqlite.Connection, assessment_id: str, data: AssessmentUpdate
) -> Assessment | None:
    fields: dict[str, object] = data.model_dump(exclude_unset=True)
    if not fields:
        return await get_assessment(db, assessment_id)

    if "criteria_snapshot" in fields and fields["criteria_snapshot"] is not None:
        # model_dump already converted it to a dict; re-serialize to JSON text.
        fields["criteria_snapshot"] = json.dumps(fields["criteria_snapshot"])
    if "completed_at" in fields and fields["completed_at"] is not None:
        completed_at = fields["completed_at"]
        if isinstance(completed_at, datetime):
            fields["completed_at"] = completed_at.isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = [*fields.values(), assessment_id]
    cursor = await db.execute(
        f"UPDATE assessment SET {set_clause} WHERE id = ?",  # noqa: S608
        values,
    )
    await db.commit()
    if cursor.rowcount == 0:
        return None
    return await get_assessment(db, assessment_id)


async def set_assessment_result(
    db: aiosqlite.Connection,
    assessment_id: str,
    *,
    grade: Grade,
    criteria_snapshot: CriteriaSnapshot,
) -> Assessment:
    """Mark an assessment complete with its final grade + criteria snapshot."""
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        UPDATE assessment
           SET status = 'complete',
               grade = ?,
               criteria_snapshot = ?,
               completed_at = ?
         WHERE id = ?
        """,
        (grade, json.dumps(criteria_snapshot.model_dump()), now, assessment_id),
    )
    await db.commit()
    result = await get_assessment(db, assessment_id)
    assert result is not None
    return result
