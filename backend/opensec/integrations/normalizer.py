"""LLM-powered finding normalizer using the singleton OpenCode process.

Accepts raw scanner data from any vendor and normalizes it into FindingCreate
records via a dedicated extraction prompt. See ADR-0022 for design rationale.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from opensec.engine.client import opencode_client
from opensec.models import FindingCreate

logger = logging.getLogger(__name__)

MAX_BATCH_SIZE = 50

# ---------------------------------------------------------------------------
# Normalizer prompt — tight extraction, few-shot, no chain-of-thought
# ---------------------------------------------------------------------------

NORMALIZER_PROMPT = """\
You are a security finding normalizer. Your job is to extract structured fields \
from raw vulnerability scanner data into a standard JSON format.

## Output schema

Each finding must match this JSON schema exactly:

```json
{
  "source_type": "string (scanner name, e.g. 'wiz', 'snyk', 'trivy')",
  "source_id": "string (unique ID from the source system)",
  "title": "string (concise finding title)",
  "description": "string or null (longer description if available)",
  "raw_severity": "string or null (original severity from the scanner, e.g. 'CRITICAL', 'High')",
  "normalized_priority": "string or null (one of: 'critical', 'high', 'medium', 'low', 'info')",
  "asset_id": "string or null (affected resource identifier)",
  "asset_label": "string or null (human-readable resource name)",
  "status": "new",
  "likely_owner": "string or null (team or person if identifiable)",
  "why_this_matters": "string or null (one sentence on business impact)"
}
```

## Rules

- Output ONLY a JSON array of objects. No explanation, no markdown fences, no text before or after.
- Every object must have `source_type`, `source_id`, and `title` — these are required.
- Set `status` to `"new"` for all findings.
- Map the scanner's severity to `normalized_priority` using: critical, high, medium, low, info.
- If a field is not present in the raw data, set it to null.
- Preserve the original `source_id` from the scanner (e.g. Wiz issue ID, Snyk issue ID).

## Examples

### Example 1: Wiz-style input

Source: wiz
Raw data:
```json
[{
  "id": "wiz-123",
  "name": "S3 bucket publicly accessible",
  "severity": "CRITICAL",
  "resource": {"id": "arn:aws:s3:::my-bucket", "name": "my-bucket"},
  "description": "The S3 bucket allows public read access."
}]
```

Output:
[{
  "source_type": "wiz",
  "source_id": "wiz-123",
  "title": "S3 bucket publicly accessible",
  "description": "The S3 bucket allows public read access.",
  "raw_severity": "CRITICAL",
  "normalized_priority": "critical",
  "asset_id": "arn:aws:s3:::my-bucket",
  "asset_label": "my-bucket",
  "status": "new",
  "likely_owner": null,
  "why_this_matters": "Public S3 buckets can expose sensitive data."
}]

### Example 2: Snyk-style input

Source: snyk
Raw data:
```json
[{
  "id": "SNYK-JS-LODASH-590103",
  "title": "Prototype Pollution in lodash",
  "severity": "high",
  "packageName": "lodash",
  "version": "4.17.15",
  "from": ["myapp@1.0.0", "lodash@4.17.15"]
}]
```

Output:
[{
  "source_type": "snyk",
  "source_id": "SNYK-JS-LODASH-590103",
  "title": "Prototype Pollution in lodash",
  "description": null,
  "raw_severity": "high",
  "normalized_priority": "high",
  "asset_id": "lodash@4.17.15",
  "asset_label": "lodash",
  "status": "new",
  "likely_owner": null,
  "why_this_matters": "Prototype pollution can cause DoS or RCE."
}]

---

Now normalize the following findings.
"""


def _build_prompt(source: str, raw_json: str) -> str:
    return f"{NORMALIZER_PROMPT}\nSource: {source}\nRaw data:\n```json\n{raw_json}\n```"


# ---------------------------------------------------------------------------
# JSON array extractor — handles fenced blocks and bare arrays
# ---------------------------------------------------------------------------


def _extract_json_array(text: str) -> list[dict[str, Any]] | None:
    """Extract a JSON array from LLM response text.

    Handles: bare JSON arrays, ```json fenced blocks, trailing commas.
    Returns None if no valid array is found.
    """
    # Strip markdown fences if present
    fenced = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1).strip() if fenced else text.strip()

    # Try to find array bounds
    start = candidate.find("[")
    if start == -1:
        return None
    # Find matching closing bracket
    depth = 0
    end = -1
    for i in range(start, len(candidate)):
        if candidate[i] == "[":
            depth += 1
        elif candidate[i] == "]":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return None

    raw = candidate[start : end + 1]

    # Remove trailing commas before ] or } (common LLM quirk)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, list):
        return None
    return parsed


# ---------------------------------------------------------------------------
# Main normalize function
# ---------------------------------------------------------------------------


async def normalize_findings(
    source: str, raw_data: list[dict[str, Any]]
) -> tuple[list[FindingCreate], list[str]]:
    """Normalize raw scanner findings via LLM extraction.

    Returns (valid_findings, errors) where errors contains human-readable
    strings for items that failed validation.
    """
    if not raw_data:
        return [], []

    if len(raw_data) > MAX_BATCH_SIZE:
        return [], [f"Batch too large: {len(raw_data)} items (max {MAX_BATCH_SIZE})"]

    # Build prompt
    raw_json = json.dumps(raw_data, indent=2)
    prompt = _build_prompt(source, raw_json)

    # Call singleton OpenCode process
    session = await opencode_client.create_session()
    await opencode_client.send_message(session.id, prompt)

    # Collect full response — last "text" event has the complete content
    # TODO: consider session cleanup for high-volume ingest
    full_text = ""
    async for event in opencode_client.stream_events(session.id):
        if event["type"] == "text":
            full_text = event["content"]
        elif event["type"] == "error":
            return [], [f"LLM error: {event.get('message', 'unknown')}"]
        elif event["type"] == "done":
            break

    if not full_text:
        return [], ["LLM returned empty response"]

    # Parse JSON array from response
    items = _extract_json_array(full_text)
    if items is None:
        return [], ["Failed to parse JSON array from LLM response"]

    # Validate each item against FindingCreate schema
    findings: list[FindingCreate] = []
    errors: list[str] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Finding {i + 1}: expected object, got {type(item).__name__}")
            continue
        # Inject source_type from the request if the LLM omitted it
        if "source_type" not in item:
            item["source_type"] = source
        try:
            findings.append(FindingCreate.model_validate(item))
        except Exception as exc:
            errors.append(f"Finding {i + 1}: {exc}")

    return findings, errors
