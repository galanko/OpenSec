"""Chat endpoints — send messages and stream responses."""

from __future__ import annotations

import json
import logging

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
    try:
        await opencode_client.send_message(session_id, body.content)
        return ChatSendResponse(session_id=session_id, status="sent")
    except Exception as e:
        logger.exception("Failed to send message to session %s", session_id)
        raise HTTPException(status_code=502, detail=f"OpenCode error: {e}") from e


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
