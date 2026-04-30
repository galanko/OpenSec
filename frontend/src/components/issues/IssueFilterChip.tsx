/**
 * IssueFilterChip — Phase 1 atom (PRD-0006).
 *
 * Toggleable filter pill with optional leading icon and trailing count badge.
 * Active state flips to `on-surface` bg with `surface-container-lowest` text;
 * inactive uses a ghost-border treatment via `outline-variant` (15% opacity is
 * the design system's blessed exception to the "no 1px solid borders" rule).
 *
 * Mirrors IPFilterChip in
 * `frontend/mockups/claude-design/PRD-0006/issues-page/atoms.jsx`.
 */
import type { ReactElement, ReactNode } from 'react'

interface IssueFilterChipProps {
  children: ReactNode
  count?: number
  active?: boolean
  icon?: string
  onClick?: () => void
}

export function IssueFilterChip({
  children,
  count,
  active = false,
  icon,
  onClick,
}: IssueFilterChipProps): ReactElement {
  const baseClasses =
    'inline-flex items-center gap-1.5 rounded-full transition-colors text-[12.5px] font-semibold pl-3 pr-1.5 py-1.5'
  const activeClasses = 'bg-on-surface text-surface-container-lowest'
  const inactiveClasses =
    'bg-surface-container-lowest text-on-surface-variant border border-outline-variant hover:bg-surface-container'

  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`${baseClasses} ${active ? activeClasses : inactiveClasses}`}
    >
      {icon && (
        <span
          className="material-symbols-outlined"
          style={{ fontSize: 14 }}
          aria-hidden="true"
        >
          {icon}
        </span>
      )}
      {children}
      {count != null && (
        <span
          className="font-mono rounded-full"
          style={{
            background: active
              ? 'rgba(255,255,255,0.18)'
              : 'var(--surface-container-high, #e3e9ec)',
            color: active ? 'var(--on-primary, #faf6ff)' : 'var(--on-surface-variant, #586064)',
            padding: '1px 7px',
            fontSize: 10.5,
            fontWeight: 600,
            minWidth: 22,
            textAlign: 'center',
            lineHeight: 1.2,
          }}
        >
          {count}
        </span>
      )}
    </button>
  )
}
