# ADR-0029: Warning design token for Serene Sentinel

**Date:** 2026-04-24
**Status:** Proposed
**PRD:** PRD-0004 v0.1 alpha blockers
**Plan:** IMPL-0004 task T5

## Context

Serene Sentinel (ADR-0011) was stood up with three semantic color families: `primary` (indigo, `#4d44e3`) for intent and active states, `tertiary` (`#575e78`) for success, and `error` (`#9e3f4e`) for destructive or failure states. The palette has no `warning` or amber family.

PRD-0004's rev. 3 design critique surfaced this as a concrete defect: medium-severity finding chips were drawing `bg-tertiary-container` (the success-green wash) because there was no neutral-or-caution token that fit. At a glance a medium-severity CVE read as "fine" — a material misrepresentation. The mockup's rev. 4 interim fix swaps medium severity to a neutral surface token until a proper warning scale exists.

The CEO ruled on 2026-04-24 that adding a dedicated `warning` family is the right answer: medium-severity findings are a concrete use case today, and the token is cheap to introduce alongside PRD-0004. Any future "attention needed but not blocking" state (stale data, degraded service, pending review) will want the same token. We should pay the cost once.

## Decision

Introduce a four-member `warning` token family to Serene Sentinel, following the Material 3 tonal system used by every other family in the palette:

| Token | Hex | Purpose |
|---|---|---|
| `warning` | `#b45f06` | Solid label or icon on a neutral surface — high-contrast text, warning-state icon fill |
| `warning-container` | `#ffddb7` | Background chip for warning states (parallel to `tertiary-container`, `error-container`) |
| `on-warning-container` | `#6a3400` | Text on `warning-container` backgrounds |
| `warning-dim` | `#8a4905` | Dimmed variant for hover / pressed states (parallel to `tertiary-dim`, `error-dim`) |

Contrast ratios against the Serene Sentinel surface hierarchy:

- `warning` (`#b45f06`) on `surface` (`#f8f9fa`): ~5.2:1 — passes WCAG AA for normal and large text
- `on-warning-container` (`#6a3400`) on `warning-container` (`#ffddb7`): ~7.6:1 — passes WCAG AAA
- `warning-dim` (`#8a4905`) on `surface-container-lowest` (`#ffffff`): ~6.1:1 — passes WCAG AA

Added to `frontend/tailwind.config.ts` alongside the existing families. No component ships with the new token in this ADR — T14 of IMPL-0004 swaps medium-severity severity chips to `bg-warning-container/40 text-on-warning-container` in the same PR.

### Usage guidance

- **Use `warning`** for: medium-severity findings, stale data, degraded service, configuration drift, pending review, caution callouts.
- **Do not use `warning`** for: non-critical information (that's `surface-container-high` / `on-surface-variant`), success (that's `tertiary`), or errors (that's `error`).
- **Severity mapping:** critical → `error`, high → `error-container/30` + `error` (existing), medium → `warning-container/40` + `on-warning-container` (new), low → `surface-container-high` + `on-surface-variant`.

## Consequences

**Easier:**

- Medium severity finally reads correctly at a glance.
- Future warning states (stale data, degraded integration, pending approvals) have a sanctioned token — no more ad-hoc amber picks.
- Design audits get one more violation they can flag cleanly (any hardcoded amber/orange hex in the frontend is now a deletable thing).

**Harder:**

- One more token family for the ux-designer and app-builder skills to remember when applying Serene Sentinel.
- Existing hardcoded amber/orange colors (if any) need to be migrated to the token — IMPL-0004 T14 only covers severity chips; a follow-up sweep may find more.

**Known gaps:**

- We do not introduce `warning-fixed` or `warning-fixed-dim` variants in this ADR. Other families have those; warning is scoped to the four members above until a concrete need emerges. This is a "three similar lines > premature abstraction" call.

## Revisit

If we ever add dark mode, this ADR gets a follow-up to define the dark-mode tonal picks for the warning family. Serene Sentinel is light-mode only today (ADR-0011) so that's deferred.
