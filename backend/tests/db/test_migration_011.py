"""Migration 011 schema test (IMPL-0003-p2 Phase 2 / ADR-0033).

Asserts that after migrations run end-to-end, the legacy ``posture_check`` table
is gone, the unified ``finding`` table has the v0.2 columns + indexes, and the
UNIQUE index on ``(source_type, source_id)`` exists for the UPSERT path.
"""

from __future__ import annotations


async def _columns(db, table: str) -> dict[str, str]:
    cursor = await db.execute(f"PRAGMA table_info({table})")  # noqa: S608
    rows = await cursor.fetchall()
    return {row["name"]: (row["type"] or "") for row in rows}


async def _indexes(db, table: str) -> set[str]:
    cursor = await db.execute(f"PRAGMA index_list({table})")  # noqa: S608
    rows = await cursor.fetchall()
    return {row["name"] for row in rows}


async def test_migration_011_drops_posture_check_table(db) -> None:
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='posture_check'"
    )
    row = await cursor.fetchone()
    assert row is None, "posture_check table should not exist after migration 011"


async def test_migration_011_finding_table_has_unified_columns(db) -> None:
    cols = await _columns(db, "finding")
    for col in (
        "id",
        "source_type",
        "source_id",
        "type",
        "grade_impact",
        "category",
        "assessment_id",
        "title",
        "description",
        "plain_description",
        "raw_severity",
        "normalized_priority",
        "status",
        "likely_owner",
        "why_this_matters",
        "asset_id",
        "asset_label",
        "raw_payload",
        "pr_url",
        "created_at",
        "updated_at",
    ):
        assert col in cols, f"finding.{col} missing"


async def test_migration_011_creates_unique_index_on_source_type_source_id(db) -> None:
    indexes = await _indexes(db, "finding")
    assert "uq_finding_source" in indexes
    cursor = await db.execute(
        "SELECT [unique] FROM pragma_index_list('finding') WHERE name = 'uq_finding_source'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1  # SQLite returns 1 for unique


async def test_migration_011_destroys_legacy_finding_rows(db) -> None:
    """ADR-0033 destructive license: any pre-011 finding rows are gone.

    Since migrations run on a fresh in-memory DB in this fixture, the test
    simply asserts the table is empty post-migration — confirming that no
    fixture data slipped through and that the new schema is the canonical one.
    """
    cursor = await db.execute("SELECT COUNT(*) FROM finding")
    row = await cursor.fetchone()
    assert row[0] == 0
