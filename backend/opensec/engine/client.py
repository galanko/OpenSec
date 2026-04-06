"""Async HTTP client for the OpenCode REST API."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import httpx

from opensec.config import settings
from opensec.engine.models import MessageInfo, SessionDetail, SessionSummary

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class OpenCodeClient:
    """Wraps the OpenCode server REST API.

    Based on the OpenAPI spec at http://localhost:4096/doc.
    Only covers the endpoints needed for the Phase 1 spike.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or settings.opencode_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # --- Sessions ---

    async def create_session(self) -> SessionSummary:
        """Create a new OpenCode session."""
        client = await self._get_client()
        resp = await client.post("/session")
        resp.raise_for_status()
        data = resp.json()
        return SessionSummary(
            id=data.get("id", data.get("sessionID", "")),
            created_at=data.get("created_at"),
        )

    async def list_sessions(self) -> list[SessionSummary]:
        """List all active sessions."""
        client = await self._get_client()
        resp = await client.get("/session")
        resp.raise_for_status()
        data = resp.json()
        sessions = data if isinstance(data, list) else data.get("sessions", [])
        return [
            SessionSummary(
                id=s.get("id", s.get("sessionID", "")),
                created_at=s.get("created_at"),
            )
            for s in sessions
        ]

    async def get_session(self, session_id: str) -> SessionDetail:
        """Get session details including messages from OpenCode."""
        client = await self._get_client()
        resp = await client.get(f"/session/{session_id}")
        resp.raise_for_status()
        data = resp.json()

        # Fetch messages from the separate /message endpoint.
        messages: list[MessageInfo] = []
        session_model = ""
        try:
            msg_resp = await client.get(f"/session/{session_id}/message")
            msg_resp.raise_for_status()
            raw_messages = msg_resp.json()
            if isinstance(raw_messages, list):
                for m in raw_messages:
                    info = m.get("info", m)
                    role = info.get("role", "")
                    msg_id = info.get("id", "")

                    # Extract model from message metadata.
                    if not session_model:
                        if role == "assistant":
                            provider_id = info.get("providerID", "")
                            model_id = info.get("modelID", "")
                            if provider_id and model_id:
                                session_model = f"{provider_id}/{model_id}"
                        elif role == "user":
                            model_info = info.get("model", {})
                            if isinstance(model_info, dict):
                                provider_id = model_info.get("providerID", "")
                                model_id = model_info.get("modelID", "")
                                if provider_id and model_id:
                                    session_model = f"{provider_id}/{model_id}"

                    # Extract text from parts array.
                    parts = m.get("parts", [])
                    text_parts = [
                        p.get("text", "")
                        for p in parts
                        if p.get("type") == "text" and p.get("text")
                    ]
                    content = "\n".join(text_parts)
                    if content:
                        messages.append(
                            MessageInfo(
                                id=msg_id,
                                role=role,
                                content=content,
                            )
                        )
        except Exception:
            logger.debug("Could not fetch messages for session %s", session_id)

        return SessionDetail(
            id=data.get("id", data.get("sessionID", session_id)),
            created_at=data.get("created_at"),
            messages=messages,
            model=session_model,
        )

    # --- Messages ---

    async def send_message(self, session_id: str, content: str) -> None:
        """Send a message to an OpenCode session.

        This is async — returns immediately. The response comes via the
        /event SSE stream as message.part.updated events.
        """
        client = await self._get_client()
        resp = await client.post(
            f"/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": content}]},
            timeout=httpx.Timeout(120.0, connect=5.0),
        )
        resp.raise_for_status()

    # --- Event streaming ---

    async def stream_events(self, session_id: str) -> AsyncIterator[dict]:
        """Subscribe to OpenCode's global SSE event stream.

        Filters events for the given session_id. Yields structured dicts:
        - {"type": "text", "content": "..."} for assistant text
        - {"type": "error", "message": "..."} for errors
        - {"type": "done"} when the session goes idle
        """
        client = await self._get_client()
        async with client.stream(
            "GET",
            "/event",
            timeout=httpx.Timeout(None, connect=5.0),
        ) as resp:
            resp.raise_for_status()
            buffer = ""
            last_text = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_str, buffer = buffer.split("\n\n", 1)
                    parsed = self._parse_sse(event_str)
                    if not parsed:
                        continue
                    try:
                        data = json.loads(parsed["data"])
                    except (json.JSONDecodeError, KeyError):
                        continue

                    event_type = data.get("type", "")
                    props = data.get("properties", {})

                    # Filter to our session
                    event_session = (
                        props.get("sessionID")
                        or props.get("info", {}).get("sessionID")
                        or props.get("part", {}).get("sessionID")
                    )
                    if event_session and event_session != session_id:
                        continue

                    if event_type == "message.part.updated":
                        part = props.get("part", {})
                        text = part.get("text", "")
                        if text and text != last_text:
                            yield {"type": "text", "content": text}
                            last_text = text

                    elif event_type == "session.error":
                        error = props.get("error", {})
                        msg = error.get("data", {}).get("message", str(error))
                        yield {"type": "error", "message": msg}

                    elif event_type == "session.idle":
                        yield {"type": "done"}
                        return

                    elif event_session == session_id:
                        # Any other session-scoped event (tool calls, etc.)
                        # signals the agent is still active.
                        yield {"type": "activity", "event_type": event_type}

    @staticmethod
    def _parse_sse(raw: str) -> dict | None:
        """Parse a single SSE event block into a dict."""
        event_type = "message"
        data_lines: list[str] = []
        for line in raw.strip().split("\n"):
            if line.startswith("event:"):
                event_type = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
            elif line.startswith(":"):
                continue  # comment
        if not data_lines:
            return None
        return {"event": event_type, "data": "\n".join(data_lines)}

    # --- Health ---

    async def health_check(self) -> bool:
        """Check if OpenCode server is responding."""
        try:
            client = await self._get_client()
            resp = await client.get("/session", timeout=2.0)
            return resp.status_code < 500
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    # --- Config ---

    async def get_config(self) -> dict:
        """GET /config — current OpenCode configuration."""
        client = await self._get_client()
        resp = await client.get("/config")
        resp.raise_for_status()
        return resp.json()

    async def update_config(self, config: dict) -> dict:
        """PATCH /config — update config at runtime (model, providers, etc.)."""
        client = await self._get_client()
        resp = await client.patch("/config", json=config)
        resp.raise_for_status()
        return resp.json()

    # --- Providers ---

    async def list_providers(self) -> dict:
        """GET /provider — all available providers with model catalogs."""
        client = await self._get_client()
        resp = await client.get("/provider")
        resp.raise_for_status()
        return resp.json()

    async def get_configured_providers(self) -> dict:
        """GET /config/providers — configured providers with defaults."""
        client = await self._get_client()
        resp = await client.get("/config/providers")
        resp.raise_for_status()
        return resp.json()

    async def get_provider_auth(self) -> dict:
        """GET /provider/auth — which providers have valid credentials."""
        client = await self._get_client()
        resp = await client.get("/provider/auth")
        resp.raise_for_status()
        return resp.json()

    # --- Auth ---

    async def set_auth(self, provider_id: str, auth: dict) -> bool:
        """PUT /auth/{provider_id} — set API key or credentials at runtime."""
        client = await self._get_client()
        resp = await client.put(f"/auth/{provider_id}", json=auth)
        resp.raise_for_status()
        return resp.json()


# Singleton instance
opencode_client = OpenCodeClient()
