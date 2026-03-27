"""Pydantic models for OpenCode API types."""

from __future__ import annotations

from datetime import datetime  # noqa: TCH003 — Pydantic needs this at runtime

from pydantic import BaseModel


class SessionSummary(BaseModel):
    id: str
    created_at: datetime | None = None


class SessionDetail(BaseModel):
    id: str
    created_at: datetime | None = None
    messages: list[MessageInfo] = []
    model: str = ""


class MessageInfo(BaseModel):
    id: str
    role: str
    content: str = ""
    created_at: datetime | None = None


class SendMessageRequest(BaseModel):
    content: str
    session_id: str


class SendMessageResponse(BaseModel):
    session_id: str
    message_id: str | None = None


class HealthStatus(BaseModel):
    opensec: str = "ok"
    opencode: str = "unknown"
    opencode_version: str = ""
    model: str = ""


class SSEEvent(BaseModel):
    event: str = "message"
    data: str = ""
