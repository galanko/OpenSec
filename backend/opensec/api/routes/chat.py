"""Chat endpoints — send messages and stream responses."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from opensec.engine.client import opencode_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatSendRequest(BaseModel):
    content: str


class ChatSendResponse(BaseModel):
    session_id: str
    status: str = "sent"


@router.post("/chat/{session_id}/send", response_model=ChatSendResponse)
async def send_message(session_id: str, body: ChatSendRequest) -> ChatSendResponse:
    """Send a message to an OpenCode session."""
    # Fire-and-forget: the SSE stream delivers the response, not this POST.
    async def _send() -> None:
        with contextlib.suppress(httpx.ReadTimeout):
            await opencode_client.send_message(session_id, body.content)

    task = asyncio.create_task(_send())
    task.add_done_callback(
        lambda t: logger.error("Background send_message failed: %s", t.exception())
        if not t.cancelled() and t.exception()
        else None
    )
    return ChatSendResponse(session_id=session_id, status="sent")


@router.get("/chat/{session_id}/stream")
async def stream_events(session_id: str) -> EventSourceResponse:
    """Stream SSE events from an OpenCode session to the browser.

    Emits three event types:
    - event: text, data: <text content>
    - event: error, data: {"message": "..."}
    - event: done, data: {}
    """

    async def event_generator():
        try:
            async for event in opencode_client.stream_events(session_id):
                event_type = event.get("type", "message")
                if event_type == "text":
                    yield {"event": "text", "data": event.get("content", "")}
                elif event_type == "error":
                    yield {
                        "event": "error",
                        "data": json.dumps({"message": event.get("message", "Unknown error")}),
                    }
                elif event_type == "done":
                    yield {"event": "done", "data": "{}"}
                    return
        except Exception:
            logger.exception("Error streaming events for session %s", session_id)
            yield {
                "event": "error",
                "data": json.dumps({"message": "Stream disconnected"}),
            }

    return EventSourceResponse(event_generator())
