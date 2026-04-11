"""AgentTemplateEngine — renders Jinja2 agent definition templates with finding context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import jinja2

if TYPE_CHECKING:
    from pathlib import Path

# The 6 agent filenames (stem only) in pipeline order.
AGENT_NAMES: list[str] = [
    "orchestrator",
    "enricher",
    "owner_resolver",
    "exposure_analyzer",
    "remediation_planner",
    "remediation_executor",
    "validation_checker",
]

_DEFAULT_TEMPLATES_DIR = None  # Resolved lazily to avoid import-time Path I/O


def _get_default_templates_dir() -> Path:
    from pathlib import Path

    return Path(__file__).parent / "templates"


@dataclass(frozen=True)
class RenderedAgent:
    """A single rendered agent definition file."""

    name: str  # e.g. "orchestrator"
    filename: str  # e.g. "orchestrator.md"
    content: str  # full rendered markdown (YAML frontmatter + prompt)


class AgentTemplateEngine:
    """Loads and renders Jinja2 templates for the 6 workspace agents.

    Synchronous — just string processing. Templates are loaded once at
    construction and re-used for each render call.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        """Initialize the engine.

        Args:
            templates_dir: Path to the templates directory. Defaults to
                the ``templates/`` directory next to this module.
        """
        resolved_dir = templates_dir or _get_default_templates_dir()
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(resolved_dir)),
            autoescape=False,
            keep_trailing_newline=True,
            undefined=jinja2.Undefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render_agent(
        self,
        name: str,
        *,
        finding: dict[str, Any],
        enrichment: dict[str, Any] | None = None,
        ownership: dict[str, Any] | None = None,
        exposure: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
        remediation: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
    ) -> RenderedAgent:
        """Render a single agent template by name.

        Args:
            name: Agent name (one of AGENT_NAMES).
            finding: Finding dict (from Finding.model_dump(mode="json")).
            enrichment..validation: Optional context section dicts.

        Returns:
            RenderedAgent with the fully rendered markdown content.

        Raises:
            ValueError: If name is not in AGENT_NAMES.
        """
        if name not in AGENT_NAMES:
            raise ValueError(
                f"Unknown agent name: {name!r}. Must be one of {AGENT_NAMES}"
            )

        template = self._env.get_template(f"{name}.md.j2")

        context = {
            "finding": finding,
            "enrichment": enrichment or {},
            "ownership": ownership or {},
            "exposure": exposure or {},
            "plan": plan or {},
            "remediation": remediation or {},
            "validation": validation or {},
            "has_enrichment": enrichment is not None,
            "has_ownership": ownership is not None,
            "has_exposure": exposure is not None,
            "has_plan": plan is not None,
            "has_remediation": remediation is not None,
            "has_validation": validation is not None,
        }

        content = template.render(**context)
        return RenderedAgent(name=name, filename=f"{name}.md", content=content)

    def render_all(
        self,
        *,
        finding: dict[str, Any],
        enrichment: dict[str, Any] | None = None,
        ownership: dict[str, Any] | None = None,
        exposure: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
        remediation: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
    ) -> list[RenderedAgent]:
        """Render all agent templates. Returns list in pipeline order."""
        kwargs = {
            "finding": finding,
            "enrichment": enrichment,
            "ownership": ownership,
            "exposure": exposure,
            "plan": plan,
            "remediation": remediation,
            "validation": validation,
        }
        return [self.render_agent(name, **kwargs) for name in AGENT_NAMES]

    def write_agents(
        self,
        agents_dir: Path,
        *,
        finding: dict[str, Any],
        enrichment: dict[str, Any] | None = None,
        ownership: dict[str, Any] | None = None,
        exposure: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
        remediation: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
    ) -> list[Path]:
        """Render all agents and write them to agents_dir.

        Returns list of written file paths.
        """
        from pathlib import Path as _Path

        agents = self.render_all(
            finding=finding,
            enrichment=enrichment,
            ownership=ownership,
            exposure=exposure,
            plan=plan,
            remediation=remediation,
            validation=validation,
        )

        paths: list[_Path] = []
        for agent in agents:
            path = _Path(agents_dir) / agent.filename
            path.write_text(agent.content)
            paths.append(path)
        return paths
