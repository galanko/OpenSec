/**
 * Shared fallback chain for rendering a finding description
 * (PRD-0004 Story 5 / IMPL-0004 T13). Every surface that renders a finding
 * description (findings list row, detail page, workspace evidence panel)
 * uses the same rule so users always see one of three clearly-shaped
 * outcomes:
 *
 *   1. plain — ``plain_description`` present and non-empty
 *   2. fallback — ``plain_description`` empty, ``description`` present
 *   3. empty — both null/empty; caller renders the "no description" link
 */

export type DescriptionResolution =
  | { kind: 'plain'; text: string }
  | { kind: 'fallback'; text: string }
  | { kind: 'empty' }

export function resolveFindingDescription(
  plain: string | null | undefined,
  raw: string | null | undefined,
): DescriptionResolution {
  const p = (plain ?? '').trim()
  if (p) return { kind: 'plain', text: p }
  const r = (raw ?? '').trim()
  if (r) return { kind: 'fallback', text: r }
  return { kind: 'empty' }
}
