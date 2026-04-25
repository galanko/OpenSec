"""DAO for the ``posture_check`` table (IMPL-0002 Milestone A2).

One row per ``(assessment_id, check_name)`` pair. ``upsert_posture_check`` replaces
any prior row for the same pair so re-running an assessment's posture sweep is
idempotent.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from opensec.models import PostureCheck, PostureCheckCreate

if TYPE_CHECKING:
    import aiosqlite


def _row_to_posture_check(row: aiosqlite.Row) -> PostureCheck:
    detail_json = row["detail"]
    return PostureCheck(
        id=row["id"],
        assessment_id=row["assessment_id"],
        check_name=row["check_name"],
        status=row["status"],
        detail=json.loads(detail_json) if detail_json else None,
        created_at=row["created_at"],
        category=_safe(row, "category"),
        pr_url=_safe(row, "pr_url"),
    )


def _safe(row: aiosqlite.Row, key: str) -> object | None:
    try:
        return row[key]
    except (IndexError, KeyError):
        return None


async def create_posture_check(
    db: aiosqlite.Connection, data: PostureCheckCreate
) -> PostureCheck:
    check_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    await db.execute(
        """
        INSERT INTO posture_check
            (id, assessment_id, check_name, status, detail, created_at, category, pr_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            check_id,
            data.assessment_id,
            data.check_name,
            data.status,
            json.dumps(data.detail) if data.detail is not None else None,
            now,
            data.category,
            data.pr_url,
        ),
    )
    await db.commit()
    cursor = await db.execute("SELECT * FROM posture_check WHERE id = ?", (check_id,))
    row = await cursor.fetchone()
    assert row is not None
    return _row_to_posture_check(row)


async def list_posture_checks_for_assessment(
    db: aiosqlite.Connection, assessment_id: str
) -> list[PostureCheck]:
    cursor = await db.execute(
        "SELECT * FROM posture_check WHERE assessment_id = ? ORDER BY created_at ASC, id ASC",
        (assessment_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_posture_check(r) for r in rows]


async def count_posture_pass_total(
    db: aiosqlite.Connection, assessment_id: str
) -> tuple[int, int]:
    """Return ``(pass_count, total_count)`` for one assessment's posture sweep."""
    cursor = await db.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END), 0) AS passes,
            COUNT(*) AS total
          FROM posture_check
         WHERE assessment_id = ?
        """,
        (assessment_id,),
    )
    row = await cursor.fetchone()
    return (row["passes"], row["total"]) if row else (0, 0)


async def upsert_posture_check(
    db: aiosqlite.Connection, data: PostureCheckCreate
) -> PostureCheck:
    """Replace any existing row for ``(assessment_id, check_name)``.

    No composite unique constraint on the table (migration is intentionally tolerant),
    so we emulate upsert by deleting prior rows then inserting a fresh one.
    """
    await db.execute(
        "DELETE FROM posture_check WHERE assessment_id = ? AND check_name = ?",
        (data.assessment_id, data.check_name),
    )
    return await create_posture_check(db, data)
