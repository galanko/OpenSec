"""Tests for seed demo data endpoint."""

from __future__ import annotations


async def test_seed_creates_findings(db_client):
    resp = await db_client.post("/api/seed")
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 5
    assert data[0]["title"] == "Apache Tomcat vulnerable version on web-prod-17"
    assert data[0]["raw_severity"] == "critical"


async def test_seed_is_idempotent(db_client):
    # First seed.
    resp1 = await db_client.post("/api/seed")
    assert resp1.status_code == 201
    assert len(resp1.json()) == 5

    # Second seed returns existing (just 1 finding from the limit=1 check).
    resp2 = await db_client.post("/api/seed")
    assert resp2.status_code == 201
    # Should return existing findings (at least 1), not create duplicates.
    assert len(resp2.json()) >= 1

    # Total findings should still be 5.
    resp3 = await db_client.get("/api/findings")
    assert len(resp3.json()) == 5
