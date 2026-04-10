import { useState, type ReactNode } from 'react'
import ConfidenceBadge from './ConfidenceBadge'
import Markdown from './Markdown'

interface ResultCardShellProps {
  title: string
  confidence?: number | null
  markdown?: string
  expandLabel?: string
  collapseLabel?: string
  /** Content shown when expanded (alongside the markdown fallback). */
  expandContent?: ReactNode
  children: ReactNode
}

export default function ResultCardShell({
  title,
  confidence,
  markdown,
  expandLabel = 'View details',
  collapseLabel = 'Hide details',
  expandContent,
  children,
}: ResultCardShellProps) {
  const [expanded, setExpanded] = useState(false)
  const hasExpandable = !!(expandContent || markdown)

  return (
    <div className="bg-surface-container-lowest rounded-2xl rounded-bl-md shadow-sm overflow-hidden">
      <div className="px-6 pt-4 pb-2 flex items-center gap-2">
        <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
        <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
          {title}
        </span>
      </div>

      <div className="px-6 pb-5 space-y-4">
        {children}

        <ConfidenceBadge confidence={confidence} />

        {hasExpandable && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs font-semibold text-primary hover:text-primary-dim transition-colors flex items-center gap-1"
          >
            <span
              className="material-symbols-outlined text-sm"
              style={{ transition: 'transform 0.2s', transform: expanded ? 'rotate(90deg)' : 'none' }}
            >
              arrow_right
            </span>
            {expanded ? collapseLabel : expandLabel}
          </button>
        )}

        {expanded && (
          <div className="space-y-3 bg-surface-container-low rounded-xl p-4">
            {expandContent}
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
