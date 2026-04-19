import { useState } from 'react'
import { useNavigate } from 'react-router'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import InlineErrorCallout from '@/components/onboarding/InlineErrorCallout'
import WizardNav from '@/components/onboarding/WizardNav'
import { OnboardingApiError } from '@/api/onboarding'
import { onboardingStorage } from './storage'

interface PreviewStep {
  icon: string
  title: string
  description: string
  duration: string
}

const STEPS: PreviewStep[] = [
  {
    icon: 'download',
    title: 'Clone and parse your repo',
    description:
      'We read your lockfiles locally and never write anything you do not review.',
    duration: '~30 s',
  },
  {
    icon: 'shield_lock',
    title: 'Check known vulnerabilities',
    description:
      'Cross-reference every dependency against OSV.dev and GHSA, grouped by fix.',
    duration: '~60 s',
  },
  {
    icon: 'rule',
    title: 'Run posture checks',
    description:
      'Branch protection, SECURITY.md, Dependabot, signed commits, secret scan.',
    duration: '~30 s',
  },
]

export default function StartAssessment() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<OnboardingApiError | null>(null)

  function handleStart() {
    const assessmentId = onboardingStorage.get('assessmentId')
    if (!assessmentId) {
      // Defensive: ConnectRepo always stashes this on success. If it's
      // missing the user probably reloaded mid-wizard — send them back.
      navigate('/onboarding/connect')
      return
    }

    // Don't block on ``/onboarding/complete`` — that endpoint returns 409 until
    // the assessment actually finishes, and keeping the user on this screen
    // defeats the progress-list UX. Navigate to the dashboard immediately; the
    // dashboard itself fires ``/complete`` when it sees status=complete.
    setError(null)
    setSubmitting(true)
    onboardingStorage.clear()
    navigate('/dashboard')
  }

  return (
    <OnboardingShell step={3}>
      <h1 className="font-headline text-3xl font-extrabold text-on-surface mb-2">
        Ready to assess
      </h1>
      <p className="text-on-surface-variant mb-8">
        Here's what happens when you click Start. Nothing is written to your
        repo without your explicit approval — every change lands as a draft
        pull request you review.
      </p>

      <ol className="space-y-3 mb-10">
        {STEPS.map((s, idx) => (
          <li
            key={s.title}
            className="flex items-start gap-4 rounded-lg bg-surface-container-lowest shadow-sm px-4 py-4"
          >
            <span className="w-8 h-8 rounded-lg bg-primary-container/60 flex items-center justify-center flex-shrink-0">
              <span
                className="material-symbols-outlined text-primary text-base"
                aria-hidden="true"
              >
                {s.icon}
              </span>
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-on-surface">
                <span className="text-on-surface-variant font-normal mr-2">
                  Step {idx + 1}
                </span>
                {s.title}
              </p>
              <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">
                {s.description}
              </p>
            </div>
            <span className="text-xs font-semibold text-on-surface-variant whitespace-nowrap">
              {s.duration}
            </span>
          </li>
        ))}
      </ol>

      {error && (
        <InlineErrorCallout
          title="We couldn't start your assessment"
          body={<>{error.message}</>}
        />
      )}

      <WizardNav
        onBack={() => navigate('/onboarding/ai')}
        onNext={handleStart}
        nextLabel={submitting ? 'Starting…' : 'Start assessment'}
        nextIcon="play_arrow"
        nextDisabled={submitting}
      />
    </OnboardingShell>
  )
}
