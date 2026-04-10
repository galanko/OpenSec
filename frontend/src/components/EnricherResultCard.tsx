import type { EnrichmentOutput } from '@/api/client'
import ResultCardShell from './ResultCardShell'

interface EnricherResultCardProps {
  data: EnrichmentOutput
  confidence?: number | null
  markdown?: string
}

function cvssColor(score: number): string {
  if (score >= 9.0) return 'bg-error'
  if (score >= 7.0) return 'bg-error/80'
  if (score >= 4.0) return 'bg-tertiary'
  return 'bg-secondary'
}

function cvssLabel(score: number): string {
  if (score >= 9.0) return 'Critical'
  if (score >= 7.0) return 'High'
  if (score >= 4.0) return 'Medium'
  return 'Low'
}

export default function EnricherResultCard({ data, confidence, markdown }: EnricherResultCardProps) {
  const expandContent = (
    <>
      {data.description && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">Description</p>
          <p className="text-sm text-on-surface-variant leading-relaxed">{data.description}</p>
        </div>
      )}
      {data.references.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">References</p>
          <ul className="space-y-1">
            {data.references.map((ref, i) => (
              <li key={i}>
                <a
                  href={ref}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-primary hover:underline break-all"
                >
                  {ref}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )

  const hasExpandable = !!(data.description || data.references.length > 0)

  return (
    <ResultCardShell
      title="Enricher result"
      confidence={confidence}
      markdown={markdown}
      expandContent={hasExpandable ? expandContent : undefined}
    >
      {/* CVE IDs */}
      {data.cve_ids.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          {data.cve_ids.map((cve) => (
            <span
              key={cve}
              className="bg-surface-container-high px-2 py-0.5 rounded text-xs font-bold text-on-surface"
            >
              {cve}
            </span>
          ))}
          <span className="text-sm text-on-surface-variant">{data.normalized_title}</span>
        </div>
      )}

      {/* CVSS bar */}
      {data.cvss_score != null && (
        <div>
          <p className="text-xs font-semibold text-on-surface mb-1">CVSS</p>
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-surface-container-high rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${cvssColor(data.cvss_score)}`}
                style={{ width: `${(data.cvss_score / 10) * 100}%` }}
              />
            </div>
            <span className="text-sm font-bold text-on-surface tabular-nums">
              {data.cvss_score.toFixed(1)}
            </span>
            <span className="text-xs text-on-surface-variant">{cvssLabel(data.cvss_score)}</span>
          </div>
        </div>
      )}

      {/* Versions + exploit */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-2">
        {data.affected_versions && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Affected</p>
            <p className="text-sm text-on-surface-variant">{data.affected_versions}</p>
          </div>
        )}
        {data.fixed_version && (
          <div>
            <p className="text-xs font-semibold text-on-surface">Fixed</p>
            <p className="text-sm text-on-surface-variant">{data.fixed_version}</p>
          </div>
        )}
        <div className="col-span-2">
          <p className="text-xs font-semibold text-on-surface">Exploit</p>
          <p className={`text-sm ${data.known_exploits ? 'text-error font-semibold' : 'text-on-surface-variant'}`}>
            {data.known_exploits ? 'Public exploit available' : 'No known exploits'}
          </p>
        </div>
      </div>
    </ResultCardShell>
  )
}
