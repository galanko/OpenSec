/**
 * TechnicalDetailsPanel — collapsible disclosure for finding technical
 * metadata (frame 3.2).
 *
 * IMPL-0002 Milestone G4. Keeps CVE / CVSS / attack vector hidden by default
 * so the plain-language body stays uncluttered.
 */

export interface TechnicalDetailsPanelProps {
  sourceId: string
  rawPayload: Record<string, unknown> | null
}

export default function TechnicalDetailsPanel({
  sourceId,
  rawPayload,
}: TechnicalDetailsPanelProps) {
  const payload = rawPayload ?? {}
  const cve = typeof payload.cve === 'string' ? payload.cve : sourceId
  const cvss =
    typeof payload.cvss_score === 'number' ||
    typeof payload.cvss_score === 'string'
      ? payload.cvss_score
      : null
  const vector =
    typeof payload.cvss_vector === 'string' ? payload.cvss_vector : null
  const attack =
    typeof payload.attack_vector === 'string' ? payload.attack_vector : null

  return (
    <details className="group mt-6 rounded-2xl bg-surface-container-low px-5 py-4">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-semibold text-on-surface">
        <span
          className="material-symbols-outlined text-on-surface-variant transition-transform group-open:rotate-90"
          style={{ fontSize: '18px' }}
          aria-hidden
        >
          chevron_right
        </span>
        Technical details
      </summary>

      <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-[auto_1fr]">
        <dt className="font-medium text-on-surface-variant">CVE</dt>
        <dd className="font-mono text-on-surface">{cve}</dd>

        {cvss != null && (
          <>
            <dt className="font-medium text-on-surface-variant">CVSS score</dt>
            <dd className="font-mono text-on-surface">{String(cvss)}</dd>
          </>
        )}

        {vector && (
          <>
            <dt className="font-medium text-on-surface-variant">CVSS vector</dt>
            <dd className="font-mono text-xs text-on-surface">{vector}</dd>
          </>
        )}

        {attack && (
          <>
            <dt className="font-medium text-on-surface-variant">Attack vector</dt>
            <dd className="text-on-surface">{attack}</dd>
          </>
        )}
      </dl>
    </details>
  )
}
