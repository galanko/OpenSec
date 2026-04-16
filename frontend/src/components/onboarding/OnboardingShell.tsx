import { type ReactNode } from 'react'
import StepProgress from './StepProgress'

export interface OnboardingShellProps {
  /** Step number to highlight in the progress bar. Omit on the Welcome
   *  screen (which has no progress bar). */
  step?: 1 | 2 | 3
  children: ReactNode
}

/**
 * Fixed-width centered column used by every onboarding page.
 * Full-bleed `surface` background; content max-width 576 px (`max-w-xl`)
 * with generous vertical padding. Depth comes from tonal layering, not
 * borders (CLAUDE.md: No-Line Rule).
 */
export default function OnboardingShell({ step, children }: OnboardingShellProps) {
  return (
    <div className="min-h-screen bg-surface">
      <div className="mx-auto max-w-xl px-6 py-12 md:px-16 md:py-16">
        {step !== undefined && <StepProgress current={step} />}
        {children}
      </div>
    </div>
  )
}
