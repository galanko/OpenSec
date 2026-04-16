"""AgentTemplateEngine — renders Jinja2 agent definition templates with finding context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import jinja2

if TYPE_CHECKING:
    from pathlib import Path

    from opensec.workspace.workspace_dir_manager import WorkspaceKind

# The 6 agent filenames (stem only) in pipeline order.
AGENT_NAMES: list[str] = [
    "orchestrator",
    "enricher",
    "owner_resolver",
    "exposure_analyzer",
    "evidence_collector",
    "remediation_planner",
    "remediation_executor",
    "validation_checker",
]

# Repo-scoped single-shot template agents (IMPL-0002 E1, E2; ADR-0024).
# Maps WorkspaceKind values to the Jinja template stem under templates/.
# Kept as string keys to avoid an import cycle with workspace_dir_manager.
REPO_ACTION_TEMPLATES: dict[str, str] = {
    "repo_action_security_md": "security_md_generator",
    "repo_action_dependabot": "dependabot_config_generator",
}

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
        evidence: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
        remediation: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
        **extra: Any,
    ) -> RenderedAgent:
        """Render a single agent template by name.

        Args:
            name: Agent name (one of AGENT_NAMES).
            finding: Finding dict (from Finding.model_dump(mode="json")).
            enrichment..validation: Optional context section dicts.
            **extra: Additional template variables (e.g. repo_url).

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
            "evidence": evidence or {},
            "plan": plan or {},
            "remediation": remediation or {},
            "validation": validation or {},
            "has_enrichment": enrichment is not None,
            "has_ownership": ownership is not None,
            "has_exposure": exposure is not None,
            "has_evidence": evidence is not None,
            "has_plan": plan is not None,
            "has_remediation": remediation is not None,
            "has_validation": validation is not None,
            **extra,
        }

        content = template.render(**context)
        return RenderedAgent(name=name, filename=f"{name}.md", content=content)

    def render_repo_action(
        self,
        kind: WorkspaceKind | str,
        *,
        repo_url: str,
        params: dict[str, Any] | None = None,
        gh_token: str | None = None,
    ) -> RenderedAgent:
        """Render a single-shot repo-action agent template (ADR-0024).

        Args:
            kind: One of ``WorkspaceKind.repo_action_*`` values (or the string
                form). Finding-pipeline agent names are rejected.
            repo_url: The target GitHub repo URL the agent will clone.
            params: Extra template variables (e.g. ``contact_email``).
            gh_token: Optional GitHub personal access token. When provided, the
                rendered prompt includes the token-export lines so the agent
                can clone and push against private repos.

        Returns:
            RenderedAgent with the template stem as ``name`` (e.g.
            ``"security_md_generator"``) and a matching ``.md`` filename.

        Raises:
            ValueError: If ``kind`` is not a repo-action kind.
        """
        kind_value = kind.value if hasattr(kind, "value") else str(kind)
        template_stem = REPO_ACTION_TEMPLATES.get(kind_value)
        if template_stem is None:
            raise ValueError(
                f"{kind_value!r} is not a repo-action kind. "
                f"Valid kinds: {sorted(REPO_ACTION_TEMPLATES)}"
            )

        template = self._env.get_template(f"{template_stem}.md.j2")
        context: dict[str, Any] = {
            "repo_url": repo_url,
            "params": params or {},
            "gh_token": gh_token,
            **(params or {}),
        }
        content = template.render(**context)
        return RenderedAgent(
            name=template_stem,
            filename=f"{template_stem}.md",
            content=content,
        )

    def render_all(
        self,
        *,
        finding: dict[str, Any],
        enrichment: dict[str, Any] | None = None,
        ownership: dict[str, Any] | None = None,
        exposure: dict[str, Any] | None = None,
        evidence: dict[str, Any] | None = None,
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
            "evidence": evidence,
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
        evidence: dict[str, Any] | None = None,
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
            evidence=evidence,
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
