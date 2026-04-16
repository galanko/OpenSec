import { cn } from '@/lib/utils'

export interface StepProgressProps {
  /** 1-indexed current step. */
  current: 1 | 2 | 3
  /** Short hint row shown on the right: "Connect · AI · Assess". */
  summary?: string
}

/**
 * Three-segment progress bar for the onboarding wizard.
 * Matches frame 1.1: a 1-pixel row of three pills above a "Step X of 3"
 * label. No `1px solid` borders — tonal fills only.
 */
export default function StepProgress({
  current,
  summary = 'Connect · AI · Assess',
}: StepProgressProps) {
  return (
    <div className="mb-10">
      <div className="flex items-center gap-2 mb-2" aria-hidden="true">
        {[1, 2, 3].map((n) => (
          <div
            key={n}
            className={cn(
              'flex-1 h-1 rounded-full transition-colors',
              n <= current ? 'bg-primary' : 'bg-surface-container-high',
            )}
          />
        ))}
      </div>
      <div
        className="flex justify-between text-xs"
        role="status"
        aria-label={`Step ${current} of 3`}
      >
        <span className="font-semibold text-primary">Step {current} of 3</span>
        <span className="text-on-surface-variant">{summary}</span>
      </div>
    </div>
  )
}
