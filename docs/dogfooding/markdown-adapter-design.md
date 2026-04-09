# MarkdownFindingSource adapter — design document

**Status:** Proposed
**Author:** OpenSec dogfooding initiative
**Date:** 2026-03-29

---

## Motivation

Security teams often produce findings in Markdown reports — from manual pen tests, architecture reviews, tool output, or consultant deliverables. A Markdown-based FindingSource adapter lets anyone import findings into OpenSec without writing code or having a scanner API.

This also enables dogfooding: we scan our own codebase with free tools, write findings as Markdown, and ingest them into our own Queue to remediate.

## MD finding format specification

Each finding is delimited by HTML comments and uses YAML-like front matter in a bullet list under specific headings. This keeps the document human-readable while being machine-parseable.

### Structure

```markdown
<!-- finding:start -->
## FINDING-ID: Title of the finding

- **source_type:** tool-name-or-manual-review
- **source_id:** FINDING-ID
- **raw_severity:** critical|high|medium|low|info
- **normalized_priority:** P1|P2|P3|P4
- **asset_id:** path/to/affected/component
- **asset_label:** Human-readable component name
- **likely_owner:** team-or-person
- **status:** new

### Description

Free-form Markdown describing the vulnerability, context, and impact.

### Evidence

Bullet points, code snippets, or references showing proof of the issue.

### Remediation hint

Suggested fix approach.

### Why this matters

Business impact and risk context.

<!-- finding:end -->
```

### Field mapping to FindingCreate

| MD field | FindingCreate field | Required | Default |
|----------|-------------------|----------|---------|
| Heading after `##` | `title` | Yes | — |
| `source_type` | `source_type` | Yes | `"markdown"` |
| `source_id` | `source_id` | Yes | auto-generated from heading |
| `raw_severity` | `raw_severity` | No | `null` |
| `normalized_priority` | `normalized_priority` | No | `null` |
| `asset_id` | `asset_id` | No | `null` |
| `asset_label` | `asset_label` | No | `null` |
| `likely_owner` | `likely_owner` | No | `null` |
| `status` | `status` | No | `"new"` |
| Description section | `description` | No | `null` |
| All sections combined | `raw_payload.sections` | No | Full parsed content |
| Evidence section | `raw_payload.evidence` | No | `null` |
| Remediation hint | `raw_payload.remediation_hint` | No | `null` |
| Why this matters | `why_this_matters` | No | `null` |

### Parser rules

1. Findings are bounded by `<!-- finding:start -->` and `<!-- finding:end -->` comments
2. The first `##` heading after `finding:start` provides the title (format: `ID: Title` or just `Title`)
3. Metadata fields are parsed from bold-prefixed list items: `- **field_name:** value`
4. Named `###` sections (Description, Evidence, Remediation hint, Why this matters) are parsed as content blocks
5. Unknown sections are preserved in `raw_payload.extra_sections`
6. Files can contain non-finding content (summaries, tables) outside the comment markers — these are ignored

## Implementation plan

### File structure

```
backend/opensec/adapters/
  __init__.py
  finding_source/
    __init__.py
    base.py              # Abstract FindingSource interface
    markdown_provider.py # MarkdownFindingSource implementation
    parser.py            # MD parsing logic (testable in isolation)
```

### Key classes

```python
# base.py
class FindingSource(ABC):
    @abstractmethod
    async def list_findings(self, filters: dict | None = None) -> list[FindingSummary]:
        ...

    @abstractmethod
    async def get_finding(self, finding_id: str) -> FindingDetail | None:
        ...

    @abstractmethod
    async def refresh(self) -> int:
        """Re-parse source, return count of new/updated findings."""
        ...


# markdown_provider.py
class MarkdownFindingSource(FindingSource):
    def __init__(self, file_path: Path):
        self._path = file_path
        self._findings: dict[str, ParsedFinding] = {}
        self._last_modified: float = 0

    async def list_findings(self, filters=None) -> list[FindingSummary]:
        await self._ensure_loaded()
        ...

    async def get_finding(self, finding_id: str) -> FindingDetail | None:
        await self._ensure_loaded()
        return self._findings.get(finding_id)

    async def refresh(self) -> int:
        """Re-parse if file has been modified."""
        ...

    async def _ensure_loaded(self):
        """Lazy-load and cache parsed findings. Re-parse on file change."""
        ...
```

### API integration

New endpoint to trigger a sync from a Markdown file:

```
POST /api/adapters/markdown/sync
Body: { "file_path": "docs/dogfooding/opensec-security-findings.md" }
Response: { "created": 5, "updated": 3, "unchanged": 5, "total": 13 }
```

The sync endpoint:
1. Parses the MD file using `parser.py`
2. For each finding, checks if `source_id` already exists in the DB
3. Creates new findings or updates existing ones
4. Returns a summary of changes

### Integration config

In the Integrations page, users configure a Markdown source:

```json
{
  "adapter_type": "finding_source",
  "provider_name": "markdown",
  "config": {
    "file_path": "docs/dogfooding/opensec-security-findings.md",
    "auto_sync": true,
    "watch_interval_seconds": 30
  }
}
```

### Parser implementation notes

The parser should:
- Use regex to find `<!-- finding:start -->` / `<!-- finding:end -->` blocks
- Parse the `## ID: Title` heading with a regex like `^##\s+(?:(\S+):\s+)?(.+)$`
- Parse metadata from `- **key:** value` patterns
- Split content by `###` headings into named sections
- Be tolerant of formatting variations (extra whitespace, missing sections)
- Return a list of `ParsedFinding` dataclasses

### Testing strategy

- Unit tests for parser with various MD formats (well-formed, minimal, malformed)
- Unit tests for MarkdownFindingSource with mock filesystem
- Integration test: parse the real dogfooding findings file and verify all 13 findings are extracted
- Edge cases: empty file, no findings, duplicate source_ids, UTF-8 content

## Migration from mock fixtures

The current `fixtures/sample_finding.json` approach can coexist with the Markdown adapter. The Markdown adapter becomes a first-class FindingSource alongside the planned Tenable/Wiz adapters. The adapter registry in `backend/opensec/adapters/` will manage provider selection.

## ADR

This design should be captured in `docs/adr/0015-markdown-finding-source.md` once approved.
