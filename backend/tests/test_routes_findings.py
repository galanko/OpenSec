"""Tests for Finding CRUD endpoints."""

from __future__ import annotations

import pytest


@pytest.fixture
def finding_payload():
    return {
        "source_type": "tenable",
        "source_id": "vuln-001",
        "title": "CVE-2024-1234 in libfoo",
        "description": "Remote code execution via buffer overflow",
        "raw_severity": "critical",
        "normalized_priority": "P1",
        "asset_id": "srv-web-01",
        "asset_label": "Web Server 01",
        "status": "new",
    }


async def test_create_finding(db_client, finding_payload):
    resp = await db_client.post("/api/findings", json=finding_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == finding_payload["title"]
    assert data["status"] == "new"
    assert data["id"]
    assert data["created_at"]


async def test_list_findings(db_client, finding_payload):
    await db_client.post("/api/findings", json=finding_payload)
    await db_client.post("/api/findings", json={**finding_payload, "source_id": "vuln-002"})

    resp = await db_client.get("/api/findings")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_findings_filter_by_status(db_client, finding_payload):
    await db_client.post("/api/findings", json=finding_payload)
    await db_client.post(
        "/api/findings", json={**finding_payload, "source_id": "vuln-002", "status": "triaged"}
    )

    resp = await db_client.get("/api/findings", params={"status": "triaged"})
    assert resp.status_code == 200
    findings = resp.json()
    assert len(findings) == 1
    assert findings[0]["status"] == "triaged"


async def test_get_finding(db_client, finding_payload):
    create_resp = await db_client.post("/api/findings", json=finding_payload)
    finding_id = create_resp.json()["id"]

    resp = await db_client.get(f"/api/findings/{finding_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == finding_id


async def test_get_finding_not_found(db_client):
    resp = await db_client.get("/api/findings/nonexistent")
    assert resp.status_code == 404


async def test_update_finding(db_client, finding_payload):
    create_resp = await db_client.post("/api/findings", json=finding_payload)
    finding_id = create_resp.json()["id"]

    resp = await db_client.patch(
        f"/api/findings/{finding_id}", json={"status": "triaged", "likely_owner": "platform-team"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "triaged"
    assert data["likely_owner"] == "platform-team"


async def test_update_finding_not_found(db_client):
    resp = await db_client.patch("/api/findings/nonexistent", json={"status": "triaged"})
    assert resp.status_code == 404


async def test_delete_finding(db_client, finding_payload):
    create_resp = await db_client.post("/api/findings", json=finding_payload)
    finding_id = create_resp.json()["id"]

    resp = await db_client.delete(f"/api/findings/{finding_id}")
    assert resp.status_code == 204

    resp = await db_client.get(f"/api/findings/{finding_id}")
    assert resp.status_code == 404


async def test_delete_finding_not_found(db_client):
    resp = await db_client.delete("/api/findings/nonexistent")
    assert resp.status_code == 404


async def test_pagination(db_client, finding_payload):
    for i in range(5):
        await db_client.post("/api/findings", json={**finding_payload, "source_id": f"v-{i}"})

    resp = await db_client.get("/api/findings", params={"limit": 2, "offset": 0})
    assert len(resp.json()) == 2

    resp = await db_client.get("/api/findings", params={"limit": 2, "offset": 4})
    assert len(resp.json()) == 1
