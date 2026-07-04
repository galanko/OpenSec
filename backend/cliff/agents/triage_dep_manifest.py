"""Deterministic dependency-manifest resolver (SP1 / ADR-0053 dep_manifest).

Clears a **dependency** finding (``location`` shape ``pkg@version``) as
``false_positive`` BEFORE the LLM Deep dive when the package provably does not
ship: every root reaching its ``(name, version)`` node is dev/test/docs/build
(no prod, no optional) AND it is not imported by any first-party shipping source.

Pure — no LLM, no network, no filesystem — keyless and CI-testable. This is a
*structural* clear like ``code_map`` (facts from the lockfile graph, not a model
hunch), so it is tier-independent under ADR-0054.

Safety (never clear a shipping dependency): the clear requires TWO independent
gates to both hold — non-prod scope AND zero shipping import sites — plus a
resolved import name. Transitive reachability of a *vulnerable API* is NOT
decided here (that is Lane B / the Deep dive); this resolver only clears the
"doesn't ship at all" case.
"""

from __future__ import annotations

from typing import Any

from cliff.agents.schemas import TriageCheck, TriageOutput, TriageProvenance

_CONF_DEP_CLEAR = 0.9

#: Scopes that mean the package reaches production (block a clear).
_SHIPPING_SCOPES = frozenset({"prod", "optional"})


def _parse_location(loc: str) -> tuple[str, str] | None:
    """``"pkg@version"`` -> ``(name, version)``; scoped npm ``@scope/name@ver`` handled.

    Splits on the LAST ``@`` so the leading ``@`` of a scoped name is preserved.
    """
    s = loc.strip()
    if "@" not in s:
        return None
    name, _, version = s.rpartition("@")
    if not name or not version:
        return None
    return name, version


def _clear(*, detail: str) -> TriageOutput:
    return TriageOutput(
        verdict="false_positive",
        confidence=_CONF_DEP_CLEAR,
        checks=[
            TriageCheck(
                eyebrow="Dependency does not ship",
                result="dev/test-only dependency",
                kind="pass",
                detail=detail,
            )
        ],
        provenance=TriageProvenance(
            steps_run=["dep_manifest_resolver"],
            exit_stage="dep_manifest_resolver",
            escalated=False,
        ),
    )


def resolve_by_dep_manifest(
    finding: dict[str, Any], dep_manifest: dict[str, Any] | None
) -> TriageOutput | None:
    """Clear *finding* if its ``pkg@version`` is a dev/test-only, unimported
    dependency; else ``None`` (fall through to Lane B / the Deep dive)."""
    if not dep_manifest:
        return None
    loc = finding.get("location")
    if not isinstance(loc, str):
        return None
    parsed = _parse_location(loc)
    if parsed is None:
        return None
    name, version = parsed

    nodes = dep_manifest.get("nodes")
    if not isinstance(nodes, list):
        return None
    matches = [
        n
        for n in nodes
        if isinstance(n, dict) and n.get("name") == name and n.get("version") == version
    ]
    if len(matches) != 1:
        # not found, or a cross-ecosystem (name, version) collision → conservative
        return None
    node = matches[0]

    scopes = node.get("scopes")
    if not isinstance(scopes, list) or not scopes:
        return None  # unknown reachability → cannot prove non-prod → don't clear
    scope_set = {s for s in scopes if isinstance(s, str)}
    if scope_set & _SHIPPING_SCOPES:
        return None  # reaches production → don't clear (Lane B decides reachability)

    import_sites = node.get("import_sites")
    if isinstance(import_sites, list) and import_sites:
        return None  # imported in first-party shipping code → don't clear (pitfall 1)

    if not node.get("import_name"):
        return None  # import name unresolved → couldn't run the import gate → don't clear (pitfall 3)

    return _clear(
        detail=(
            f"{name}@{version} ({node.get('ecosystem', '?')}) reaches only "
            f"{sorted(scope_set)} roots and is imported by no shipping first-party "
            f"source (declared_in={node.get('declared_in') or 'transitive'})"
        )
    )
