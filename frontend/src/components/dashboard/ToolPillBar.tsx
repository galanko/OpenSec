/**
 * ToolPillBar — the brand-trust signal at the top of the dashboard
 * (PRD-0003 v0.2 / ADR-0032). Renders the three scanner identity pills
 * (Trivy, Semgrep, posture) with state + result counts.
 *
 * States: pending | active | done | skipped.
 *   - active: filled background + animate-pulse-subtle
 *   - done:   filled-tertiary background + check_circle icon, result tail visible
 *   - skipped: muted, line-through
 *   - pending: surface-container muted background
 *
 * Reference: frontend/mockups/claude-design/surfaces/shared.jsx::ToolPillBar.
 */

import type { components } from '@/api/types'

type AssessmentTool = components['schemas']['AssessmentTool']

export interface ToolPillBarProps {
  tools: AssessmentTool[]
  size?: 'sm' | 'md'
}

const cx = (...xs: (string | false | null | undefined)[]) =>
  xs.filter(Boolean).join(' ')

export default function ToolPillBar({ tools, size = 'md' }: ToolPillBarProps) {
  const padding =
    size === 'sm' ? 'px-2.5 py-1 text-[11px]' : 'px-3 py-1.5 text-xs'
  return (
    <div
      data-testid="tool-pill-bar"
      className="flex items-center gap-2 flex-wrap"
    >
      {tools.map((tool) => {
        const base =
          'inline-flex items-center gap-1.5 rounded-full font-semibold transition-colors'
        let cls = ''
        let icon = tool.icon
        if (tool.state === 'active') {
          cls =
            'bg-primary-container text-on-primary-container animate-pulse-subtle'
        } else if (tool.state === 'done') {
          cls = 'bg-tertiary-container/60 text-on-tertiary-container'
          icon = 'check_circle'
        } else if (tool.state === 'skipped') {
          cls =
            'bg-surface-container-high text-on-surface-variant/70 line-through'
        } else {
          cls = 'bg-surface-container-high text-on-surface-variant'
        }
        return (
          <span
            key={tool.id}
            data-testid={`tool-pill-${tool.id}`}
            data-state={tool.state}
            className={cx(base, cls, padding)}
          >
            <span
              className={cx(
                'material-symbols-outlined',
                tool.state === 'done' ? 'msym-filled' : '',
              )}
              style={{ fontSize: size === 'sm' ? 13 : 14 }}
              aria-hidden
            >
              {icon}
            </span>
            <span>{tool.label}</span>
            {tool.state === 'done' && tool.result && (
              <span className="ml-1 font-medium opacity-70">
                · {tool.result.text}
              </span>
            )}
          </span>
        )
      })}
    </div>
  )
}
