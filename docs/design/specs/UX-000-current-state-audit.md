# UX-000: Current state audit

**Status:** Complete
**Date:** 2026-04-09
**Author:** UX team (bootstrap)

---

## Design system compliance scorecard

**Overall: 4 of 17 components fully compliant (24%)**

The main violations are systematic — the same two issues repeat across most components:
1. **No-Line Rule violations** — `border` classes used instead of ghost borders or tonal shifts
2. **Arbitrary Tailwind colors** — `green-*`, `red-*`, `indigo-*` used instead of design tokens

| Component | No-Line | Colors | Sentence case | Icons | Fonts | Overall |
|-----------|---------|--------|--------------|-------|-------|---------|
| PageShell | Pass | Pass | Pass | N/A | Pass | **Pass** |
| FindingRow | Pass | Pass | Pass | Pass | Pass | **Pass** |
| SeverityBadge | Pass | Pass | Pass | Pass | Pass | **Pass** |
| EmptyState | Pass | Pass | Pass | Pass | Pass | **Pass** |
| Markdown | Pass | Pass | Pass | N/A | Pass | **Pass** |
| ActionChips | Fail | Pass | Pass | N/A | Pass | Fail |
| ActionButton | Fail | Pass | Pass | Pass | Pass | Fail |
| AgentRunCard | Fail | Fail | Pass | N/A | Pass | Fail |
| ResultCard | Fail | Pass | Pass | N/A | Pass | Fail |
| WorkspaceSidebar | Fail | Pass | Pass | N/A | Pass | Fail |
| ListCard | Fail | Pass | N/A | N/A | N/A | Fail |
| HistoryCard | Fail | Fail | Pass | Pass | Pass | Fail |
| HistoryDetail | Fail | Pass | Pass | Pass | Pass | Fail |
| SideNav | Fail | Pass | Pass | Pass | Pass | Fail |
| TopBar | Fail | Fail | Pass | Pass | Pass | Fail |
| ProviderSettings | Pass* | Fail | Pass | Pass | Pass | Fail |
| IntegrationSettings | Pass* | Fail | Pass | Pass | Pass | Fail |

*Form inputs use `@tailwindcss/forms` plugin which handles borders; remaining violations are in status indicators.

---

## Design debt: No-Line Rule violations

13 of 17 components use `border` classes. These need to be replaced with ghost borders (outline-variant at 15% opacity) or tonal layering (background color shifts).

### High-impact fixes (visible on every page):

| Component | Violation | Fix |
|-----------|-----------|-----|
| **SideNav** | `border-r border-outline-variant/20` divider, `border-r-2 border-primary` active indicator | Replace divider with tonal shift (`bg-surface-container` edge). Replace active indicator with background highlight |
| **TopBar** | `border-b-2 border-primary` active nav indicator | Replace with background highlight or underline via box-shadow |
| **ListCard** | `border border-transparent` + `hover:border-primary/5` | Remove border entirely, rely on shadow for hover |

### Medium-impact fixes (visible in specific flows):

| Component | Violation | Fix |
|-----------|-----------|-----|
| **WorkspaceSidebar** | `border-l border-surface-container`, `border border-surface-container/50` on sections | Replace left border with tonal shift. Replace section borders with spacing + background |
| **ActionChips** | `border border-primary/10` | Remove border, use tonal background (`bg-primary-container/10`) |
| **ActionButton** | `border border-outline-variant/30` (outline variant) | Use ghost border: `shadow-[0_0_0_1px_rgba(var(--outline-variant),0.15)]` or tonal bg |
| **ResultCard** | 3 borders on card, header, buttons | Replace with tonal layering between sections |
| **AgentRunCard** | 3 borders across states | Replace with tonal backgrounds per state |
| **HistoryCard** | State badges use borders | Remove borders from badge, rely on bg + text color |
| **HistoryDetail** | `border-t` separator, `border` on message bubbles | Replace with spacing + tonal shift |

---

## Design debt: Arbitrary color violations

Components using Tailwind default colors instead of design tokens. This is the second most common violation.

| Component | Arbitrary colors | Should be |
|-----------|-----------------|-----------|
| **AgentRunCard** | `bg-indigo-50/80`, `border-indigo-100` | `bg-primary-container/30`, `border-primary/10` |
| **HistoryCard** | `text-green-700`, `bg-green-100`, `border-green-200` | `text-tertiary`, `bg-tertiary-container/30` |
| **TopBar** | `bg-green-500` (health indicator) | `bg-tertiary` or a dedicated `status-ok` token |
| **ProviderSettings** | `text-green-500/600`, `bg-green-500` | `text-tertiary`, `bg-tertiary` |
| **IntegrationSettings** | `text-green-700`, `bg-green-50`, `bg-green-400`, `bg-red-50`, `text-red-800` | `text-tertiary`/`bg-tertiary-container`, `text-error`/`bg-error-container` |

**Pattern:** Green is used for "connected/success/ok" states. These should all use `tertiary` tokens (green-tinted in our system). Red states should use `error` tokens (already correct in most places).

---

## Missing patterns

### Focus-visible states (critical for accessibility)

No component has explicit `focus-visible:ring-*` styling except form inputs (via `@tailwindcss/forms`). Every interactive element needs this:
- Buttons: `focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-2`
- Cards: `focus-visible:outline-2 focus-visible:outline-primary/40`
- Nav items: `focus-visible:ring-2 focus-visible:ring-primary/40`

### Error states

| Page | Error handling |
|------|---------------|
| Queue | None — no error boundary, no "failed to load" state |
| Workspace | Chat errors appear as error-styled messages in thread (partial) |
| History | None — no error boundary |
| Settings | Child components handle some errors (partial) |

**Needed:** A shared `ErrorState` component (similar to `EmptyState`) for page-level API failures.

### Loading states

| Component | Has loading? |
|-----------|-------------|
| Pages (Queue, History) | Yes — spinning circle |
| WorkspacePage | Yes — spinner |
| SettingsPage | No — delegates to children |
| ActionChips | No — chips disabled but no spinner on the active chip |
| ActionButton | No — no loading variant |
| HistoryCard export | No — no indicator during export |

**Needed:** A `loading` prop on `ActionButton` and `ActionChips` that shows a spinner.

### Confirmation dialogs

No confirmation before destructive actions:
- Resolving a workspace (irreversible state change)
- Deleting an API key
- Deleting an integration

**Needed:** A shared `ConfirmDialog` component.

### Transitions and animations

Current animations:
- Agent thinking: bouncing dots (CSS animation)
- Agent running: pulse animation
- Streaming: text appearing incrementally

Missing:
- Page transitions (no animation between routes)
- List item enter/exit (no animation when filtering)
- Sidebar section expand/collapse
- Tab switching (HistoryDetail tabs switch instantly)

---

## Mockup vs implementation drift

### Queue page drift

| Mockup feature | Implementation status |
|---------------|---------------------|
| Finding list with severity, title, metadata | Built |
| Filter + sort controls | Built (dropdown style differs from mockup) |
| "Solve" button per row | Built |
| Right sidebar "Sentinel Insights" panel | **Not built** — significant feature gap |
| Educational card ("Automated remediation is learning") | **Not built** |
| Blocked state with opacity/grayscale | **Not built** |

### Workspace page drift

| Mockup feature | Implementation status |
|---------------|---------------------|
| Header with finding info + actions | Built |
| Chat with streaming | Built |
| Action chips | Built |
| Right sidebar with 7 sections | Built |
| Structured agent result cards (headers, confidence, evidence) | **Partial** — results render as markdown, not structured cards |
| "Agent Running" card with animated dots | **Partial** — thinking indicator exists but less elaborate |

### History page drift

| Mockup feature | Implementation status |
|---------------|---------------------|
| Workspace list with search | Built |
| State tabs + sort | Built |
| Export as markdown | Built |
| Stats dashboard (resolved count, avg time, success rate) | **Not built** — significant feature gap |
| AI Insight gradient card | **Not built** |
| "Reuse Plan" button | **Not built** |
| Pagination | **Not built** (client-side filtering only) |
| Calendar/date range filter | **Not built** |

### Settings page drift

| Mockup feature | Implementation status |
|---------------|---------------------|
| Provider/model selection | Built (via ProviderSettings child) |
| API key management | Built |
| Integration setup + testing | Built (via IntegrationSettings child) |
| Internal sidebar nav (Model, Agent, Workspace, Preferences) | **Not built** |
| Agent settings (threat hunting toggle, auto-remediation) | **Not built** |
| Workspace defaults (quarantine, notify, ignore, log-only) | **Not built** |
| App preferences (language, notifications) | **Not built** |
| Save/Discard buttons | **Not built** |

### Integrations page

No separate `IntegrationsPage.tsx` exists. Integration management is embedded in SettingsPage via `IntegrationSettings` component. The mockup shows a dedicated page with richer layout. **The mockup's dedicated Integrations page was never built as a separate route.**

---

## Recommendations (prioritized by impact)

### P0: Fix systematic violations (affects everything)

1. **Create a `ghost-border` utility** — add to Tailwind config: `'ghost-border': '0 0 0 1px rgba(var(--outline-variant), 0.15)'` as a box-shadow. Replace all `border border-*` with this or with tonal shifts.
2. **Replace all arbitrary green/red** with `tertiary`/`error` tokens. Grep for `green-`, `red-`, `indigo-` in frontend/src/ and replace systematically.
3. **Add `focus-visible` to all interactive elements** — create a shared utility class or Tailwind plugin.

### P1: Add missing states (improves reliability feel)

4. **Create `ErrorState` component** — similar to EmptyState, for API failures.
5. **Add `loading` prop to ActionButton** — spinner replaces text during async operations.
6. **Add error boundaries** to each page — catch render errors gracefully.

### P2: Close mockup gaps (increases product value)

7. **History stats dashboard** — the mockup's stats bento grid (resolved count, avg time, success rate) adds significant value perception.
8. **Structured agent result cards** — replace raw markdown output with card-based results matching the mockup's headers + confidence badges + evidence sections.
9. **Queue search** — already in BACKLOG, but the mockup shows it prominently.

### P3: Polish (reduces perceived jank)

10. **Add confirmation dialogs** for resolve, delete key, delete integration.
11. **Add list enter/exit animations** for filter transitions.
12. **Add page transitions** between routes.

---

_This audit establishes the UX baseline as of 2026-04-09. All future UX work should reduce the violation count and close mockup gaps._
