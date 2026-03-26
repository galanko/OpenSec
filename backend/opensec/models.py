"""Pydantic domain models for OpenSec entities."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime
from typing import Any, Literal

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

FindingStatus = Literal[
    "new", "triaged", "in_progress", "remediated", "validated", "closed", "exception"
]


class FindingCreate(BaseModel):
    source_type: str
    source_id: str
    title: str
    description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus = "new"
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus | None = None
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None


class Finding(BaseModel):
    id: str
    source_type: str
    source_id: str
    title: str
    description: str | None = None
    raw_severity: str | None = None
    normalized_priority: str | None = None
    asset_id: str | None = None
    asset_label: str | None = None
    status: FindingStatus = "new"
    likely_owner: str | None = None
    why_this_matters: str | None = None
    raw_payload: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

WorkspaceState = Literal["open", "waiting", "ready_to_close", "closed", "reopened"]


class WorkspaceCreate(BaseModel):
    finding_id: str
    state: WorkspaceState = "open"
    current_focus: str | None = None


class WorkspaceUpdate(BaseModel):
    state: WorkspaceState | None = None
    current_focus: str | None = None
    active_plan_version: int | None = None
    linked_ticket_id: str | None = None
    validation_state: str | None = None


class Workspace(BaseModel):
    id: str
    finding_id: str
    state: WorkspaceState = "open"
    current_focus: str | None = None
    active_plan_version: int | None = None
    linked_ticket_id: str | None = None
    validation_state: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

MessageRole = Literal["user", "assistant", "system", "agent"]


class MessageCreate(BaseModel):
    role: MessageRole
    content_markdown: str | None = None
    linked_agent_run_id: str | None = None


class Message(BaseModel):
    id: str
    workspace_id: str
    role: MessageRole
    content_markdown: str | None = None
    linked_agent_run_id: str | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# AgentRun
# ---------------------------------------------------------------------------

AgentRunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]

AgentType = Literal[
    "finding_enricher",
    "owner_resolver",
    "exposure_analyzer",
    "remediation_planner",
    "validation_checker",
]


class AgentRunCreate(BaseModel):
    agent_type: str
    status: AgentRunStatus = "queued"
    input_json: dict[str, Any] | None = None


class AgentRunUpdate(BaseModel):
    status: AgentRunStatus | None = None
    summary_markdown: str | None = None
    confidence: float | None = None
    evidence_json: dict[str, Any] | None = None
    structured_output: dict[str, Any] | None = None
    next_action_hint: str | None = None


class AgentRun(BaseModel):
    id: str
    workspace_id: str
    agent_type: str
    status: AgentRunStatus = "queued"
    input_json: dict[str, Any] | None = None
    summary_markdown: str | None = None
    confidence: float | None = None
    evidence_json: dict[str, Any] | None = None
    structured_output: dict[str, Any] | None = None
    next_action_hint: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# SidebarState
# ---------------------------------------------------------------------------


class SidebarStateUpdate(BaseModel):
    summary: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    owner: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    definition_of_done: dict[str, Any] | None = None
    linked_ticket: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    similar_cases: dict[str, Any] | None = None


class SidebarState(BaseModel):
    workspace_id: str
    summary: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    owner: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    definition_of_done: dict[str, Any] | None = None
    linked_ticket: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    similar_cases: dict[str, Any] | None = None
    updated_at: datetime


# ---------------------------------------------------------------------------
# Read-only models (schema exists, no CRUD endpoints in Phase 3)
# ---------------------------------------------------------------------------


class TicketLink(BaseModel):
    id: str
    workspace_id: str
    provider: str
    external_key: str
    title: str | None = None
    status: str | None = None
    assignee: str | None = None
    payload_snapshot: dict[str, Any] | None = None
    last_synced_at: datetime | None = None


class ValidationResult(BaseModel):
    id: str
    workspace_id: str
    provider: str
    state: Literal["not_started", "pending", "fixed", "still_active", "uncertain"] = "not_started"
    details_markdown: str | None = None
    evidence: dict[str, Any] | None = None
    created_at: datetime


class AppSetting(BaseModel):
    key: str
    value: dict[str, Any] | None = None
    updated_at: datetime


class IntegrationConfig(BaseModel):
    id: str
    adapter_type: str
    provider_name: str
    enabled: bool = True
    config: dict[str, Any] | None = None
    last_test_result: dict[str, Any] | None = None
    updated_at: datetime
