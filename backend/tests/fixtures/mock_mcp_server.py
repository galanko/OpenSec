#!/usr/bin/env python3
"""Minimal stdio MCP server for testing.

Responds to ``initialize`` and ``tools/list`` JSON-RPC requests.
Used by E2E tests to verify that workspace opencode.json configs
correctly reference an MCP server that OpenCode can start.

Usage:
    python -m tests.fixtures.mock_mcp_server

Environment:
    MOCK_MCP_TOKEN  — If set, the server validates that this token is present
                      (simulates credential injection).
"""

from __future__ import annotations

import json
import os
import sys


def _respond(request_id: int | str, result: dict) -> None:
    """Write a JSON-RPC response to stdout."""
    response = json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})
    # MCP uses content-length delimited framing over stdio.
    header = f"Content-Length: {len(response)}\r\n\r\n"
    sys.stdout.write(header + response)
    sys.stdout.flush()


def _error(request_id: int | str, code: int, message: str) -> None:
    """Write a JSON-RPC error to stdout."""
    response = json.dumps({
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    })
    header = f"Content-Length: {len(response)}\r\n\r\n"
    sys.stdout.write(header + response)
    sys.stdout.flush()


def main() -> None:
    """Run the mock MCP server, reading JSON-RPC from stdin."""
    token = os.environ.get("MOCK_MCP_TOKEN", "")

    while True:
        # Read content-length header.
        line = sys.stdin.readline()
        if not line:
            break  # EOF

        line = line.strip()
        if not line.lower().startswith("content-length:"):
            continue

        content_length = int(line.split(":")[1].strip())

        # Read blank line.
        sys.stdin.readline()

        # Read body.
        body = sys.stdin.read(content_length)
        if not body:
            break

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        request_id = request.get("id")

        if method == "initialize":
            _respond(request_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-mcp-server", "version": "0.1.0"},
            })
        elif method == "tools/list":
            _respond(request_id, {
                "tools": [
                    {
                        "name": "mock_echo",
                        "description": "Echoes the input (test tool).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"},
                            },
                        },
                    },
                ],
            })
        elif method == "tools/call":
            tool_name = request.get("params", {}).get("name", "")
            if tool_name == "mock_echo":
                msg = request.get("params", {}).get("arguments", {}).get("message", "")
                if token and not os.environ.get("MOCK_MCP_TOKEN"):
                    _error(request_id, -1, "Missing MOCK_MCP_TOKEN")
                else:
                    _respond(request_id, {
                        "content": [{"type": "text", "text": f"echo: {msg}"}],
                    })
            else:
                _error(request_id, -32601, f"Unknown tool: {tool_name}")
        else:
            _error(request_id, -32601, f"Unknown method: {method}")


if __name__ == "__main__":
    main()
