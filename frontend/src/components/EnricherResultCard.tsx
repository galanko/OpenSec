import { useState } from 'react'
import type { EnrichmentOutput } from '@/api/client'
import ConfidenceBadge from './ConfidenceBadge'
import Markdown from './Markdown'

interface EnricherResultCardProps {
  data: EnrichmentOutput
  confidence?: number | null
  markdown?: string
}

function cvssColor(score: number | null | undefined): string {
  if (score == null) return 'bg-on-surface-variant/20'
  if (score >= 9.0) return 'bg-error'
  if (score >= 7.0) return 'bg-error/80'
  if (score >= 4.0) return 'bg-tertiary'
  return 'bg-secondary'
}

function cvssLabel(score: number | null | undefined): string {
  if (score == null) return 'Unknown'
  if (score >= 9.0) return 'Critical'
  if (score >= 7.0) return 'High'
  if (score >= 4.0) return 'Medium'
  return 'Low'
}

export default function EnricherResultCard({ data, confidence, markdown }: EnricherResultCardProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-surface-container-lowest rounded-2xl rounded-bl-md shadow-sm overflow-hidden">
      {/* Agent label */}
      <div className="px-6 pt-4 pb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          Enricher result
        </span>
      </div>

      <div className="px-6 pb-5 space-y-4">
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

        {/* Confidence */}
        <div className="flex items-center justify-between">
          <ConfidenceBadge confidence={confidence} />
        </div>

        {/* Expandable details */}
        {(data.description || data.references.length > 0 || markdown) && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-semibold text-primary hover:text-primary-dim transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-sm" style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }}>
              arrow_right
            </span>
            {expanded ? 'Hide details' : 'View details'}
          </button>
        )}

        {expanded && (
          <div className="space-y-3 bg-surface-container-low rounded-xl p-4">
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
            {markdown && (
              <div>
                <p className="text-xs font-semibold text-on-surface mb-1">Full analysis</p>
                <Markdown content={markdown} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
