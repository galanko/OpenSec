import CriteriaMeter from './CriteriaMeter'

export interface CompletionProgressCardProps {
  criteriaMet: number
  criteriaTotal: number
  repoName: string
}

export default function CompletionProgressCard({
  criteriaMet,
  criteriaTotal,
  repoName,
}: CompletionProgressCardProps) {
  const remaining = Math.max(0, criteriaTotal - criteriaMet)
  const progressLabel =
    remaining === 0
      ? `${criteriaMet} criteria met · all complete`
      : `${criteriaMet} criteria met · ${remaining} remaining`

  return (
    <section
      data-testid="CompletionProgressCard"
      className="flex items-start gap-6 rounded-3xl bg-surface-container-low p-8"
      aria-label="Completion progress"
    >
      <ShieldIllustration />

      <div className="flex-1 min-w-0">
        <h2 className="font-headline text-2xl font-bold text-on-surface">
          Completion progress
        </h2>
        <p className="mt-1 text-sm text-on-surface-variant">
          Five criteria earn security completion for{' '}
          <span className="font-semibold text-on-surface">{repoName}</span>.
        </p>

        <div className="mt-5">
          <CriteriaMeter met={criteriaMet} total={criteriaTotal} />
        </div>

        <p className="mt-3 text-sm font-medium text-on-surface-variant">
          {progressLabel}
        </p>
      </div>
    </section>
  )
}

function ShieldIllustration() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 54 64"
      width={54}
      height={64}
      className="flex-none text-primary opacity-40"
    >
      <path
        fill="currentColor"
        d="M27 0 0 10v22c0 14 11 27 27 32 16-5 27-18 27-32V10L27 0Zm0 58C14 53 4 41 4 32V13l23-9 23 9v19c0 9-10 21-23 26Z"
      />
      <path
        fill="currentColor"
        d="m22 33-6-6-3 3 9 9 19-19-3-3-16 16Z"
      />
    </svg>
  )
}
