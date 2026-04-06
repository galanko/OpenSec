"""Agent execution error types."""

from __future__ import annotations


class AgentExecutionError(Exception):
    """Base class for agent execution errors."""


class AgentTimeoutError(AgentExecutionError):
    """Agent did not complete within the timeout budget."""


class AgentProcessError(AgentExecutionError):
    """The workspace's OpenCode process is unavailable or crashed."""


class AgentBusyError(AgentExecutionError):
    """Another agent is already running in this workspace."""
