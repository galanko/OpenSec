/**
 * DescriptionFallbackNote — muted single-line note rendered below a finding
 * description when the UI had to fall back from ``plain_description`` to the
 * raw scanner ``description`` (PRD-0004 Story 5 / IMPL-0004 T13).
 */

export default function DescriptionFallbackNote() {
  return (
    <p
      data-testid="description-fallback-note"
      className="mt-2 inline-flex items-center gap-1 text-xs text-on-surface-variant"
    >
      <span className="material-symbols-outlined text-sm" aria-hidden>
        info
      </span>
      Auto-summary unavailable — showing raw scanner description
    </p>
  )
}
