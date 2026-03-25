# ADR-0001: Use OpenCode as the AI Engine (Git Submodule)

**Date:** 2026-03-25
**Status:** Accepted

## Context

OpenSec needs an AI engine to power code analysis, remediation planning, and agent execution. Building an LLM orchestration layer from scratch would be a massive effort that distracts from the security product itself.

[OpenCode](https://github.com/anomalyco/opencode) is an active, MIT-licensed open-source coding agent. It provides:

- A headless HTTP server (`opencode serve`) with REST API and OpenAPI 3.1 spec
- Configurable primary agents and subagents with custom prompts and tool permissions
- Support for 75+ LLM providers (Anthropic, OpenAI, Google, AWS Bedrock, etc.)
- A TypeScript SDK for programmatic control
- Server-sent events for real-time streaming
- Session management, memory, and compaction

The server/client architecture means we can use OpenCode's engine without inheriting its terminal UI.

## Decision

Use `anomalyco/opencode` as the AI runtime engine, integrated as a **Git submodule** under `engine/opencode/`.

- OpenCode runs as a managed subprocess inside the Docker container
- FastAPI backend communicates with it via its REST API on an internal port
- We use OpenCode's agent/subagent model to define our cyber-specific agents
- We do NOT use or depend on OpenCode's terminal UI

## Consequences

- **Easier:** We get agent orchestration, model provider support, tool execution, and session management for free.
- **Easier:** Upstream improvements flow in via submodule updates.
- **Harder:** We depend on an external project's API stability. Breaking changes in OpenCode require adaptation.
- **Harder:** Go runtime must be present in the Docker image to build/run OpenCode.
- **Risk:** If OpenCode's architecture diverges from our needs, we may need to fork internals later. The submodule approach keeps this option open.
