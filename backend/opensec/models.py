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
    workspace_dir: str | None = None
    context_version: int = 0
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
    "remediation_executor",
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
    pull_request: dict[str, Any] | None = None


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
    pull_request: dict[str, Any] | None = None
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
    action_tier: int = 0  # 0=read-only, 1=enrichment, 2=mutation
    updated_at: datetime


class IntegrationConfigCreate(BaseModel):
    adapter_type: str
    provider_name: str
    enabled: bool = True
    config: dict[str, Any] | None = None
    action_tier: int = 0


class IntegrationConfigUpdate(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    action_tier: int | None = None


# ---------------------------------------------------------------------------
# Settings API request/response models
# ---------------------------------------------------------------------------


class ModelUpdateRequest(BaseModel):
    model_full_id: str


class ApiKeyCreate(BaseModel):
    provider: str
    key: str


class ApiKeyResponse(BaseModel):
    provider: str
    key_masked: str
    has_credentials: bool = True
    updated_at: datetime | None = None


class ProviderInfo(BaseModel):
    id: str
    name: str
    env: list[str] = []
    models: dict[str, Any] = {}


class ModelConfig(BaseModel):
    model_full_id: str
    provider: str = ""
    model_id: str = ""


# ---------------------------------------------------------------------------
# Integration credential models (Phase I-0)
# ---------------------------------------------------------------------------


class CredentialCreate(BaseModel):
    key_name: str
    value: str


class CredentialInfo(BaseModel):
    key_name: str
    created_at: str
    rotated_at: str | None = None


class TestConnectionResult(BaseModel):
    success: bool
    message: str
    details: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Workspace integration models (Phase I-1)
# ---------------------------------------------------------------------------


class WorkspaceIntegration(BaseModel):
    integration_id: str
    provider_name: str
    registry_id: str
    action_tier: int = 0  # 0=read-only, 1=enrichment, 2=mutation
    capabilities: list[str] = []
    status: str = "connected"  # "connected", "missing_credentials", "disabled"


# ---------------------------------------------------------------------------
# Integration health models (Phase I-2)
# ---------------------------------------------------------------------------


class IntegrationHealthStatus(BaseModel):
    integration_id: str
    registry_id: str
    provider_name: str
    credential_status: str = "unchecked"  # "ok", "missing", "decrypt_error", "unchecked"
    connection_status: str = "unchecked"  # "ok", "error", "unchecked", "timeout"
    last_checked: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Finding ingest models (ADR-0022 + ADR-0023)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Finding ingest models (ADR-0022 + ADR-0023)
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    source: str
    raw_data: list[dict[str, Any]]
    model: str | None = None  # optional model override
    chunk_size: int = 10  # items per LLM call (1-50)
    dry_run: bool = False  # estimate only, do not create job


class IngestJobResponse(BaseModel):
    job_id: str
    status: str
    total_items: int
    chunk_size: int
    total_chunks: int
    estimated_tokens: int | None = None
    poll_url: str


class IngestJobProgress(BaseModel):
    job_id: str
    status: str
    total_items: int
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    findings_created: int
    errors: list[str]
    created_at: str
    updated_at: str


class IngestResult(BaseModel):
    """Deprecated — kept for backward compatibility. New code uses IngestJobResponse."""

    created: list[Finding]
    errors: list[str]
