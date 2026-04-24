import { useEffect } from 'react'
import { useNavigate } from 'react-router'
import OnboardingShell from '@/components/onboarding/OnboardingShell'
import InlineErrorCallout from '@/components/onboarding/InlineErrorCallout'
import WizardNav from '@/components/onboarding/WizardNav'
import AssessmentProgressList from '@/components/dashboard/AssessmentProgressList'
import { useAssessmentStatus } from '@/api/dashboard'
import { onboardingStorage } from './storage'

/**
 * Onboarding frame 1.5 — "Ready to assess".
 *
 * The assessment was already kicked off at step 1 (``/onboarding/repo``),
 * so by the time the user reaches this screen a real run is usually in
 * flight. Rather than show a static preview and then redirect to the
 * dashboard (where the run often completes before the user sees anything),
 * we render the same ``AssessmentProgressList`` the dashboard uses and
 * auto-navigate to ``/dashboard`` when the backend flips to ``complete``.
 *
 * Consistency goal: onboarding and re-assessment both show live progress,
 * both end at the dashboard, both using one component.
 */
export default function StartAssessment() {
  const navigate = useNavigate()
  const assessmentId = onboardingStorage.get('assessmentId')

  // Defensive: ConnectRepo always stashes an id on success. If it's missing
  // the user probably reloaded mid-wizard — send them back to rebuild state.
  useEffect(() => {
    if (!assessmentId) navigate('/onboarding/connect')
  }, [assessmentId, navigate])

  const { data, isError } = useAssessmentStatus(assessmentId)
  const status = data?.status

  // Auto-advance to the dashboard as soon as the backend reports complete.
  // A short dwell lets the "all five steps done" visual register before the
  // route change — same motivation as the 1.4 s verified-card dwell.
  useEffect(() => {
    if (status !== 'complete') return
    const timer = window.setTimeout(() => {
      onboardingStorage.clear()
      navigate('/dashboard')
    }, 900)
    return () => window.clearTimeout(timer)
  }, [status, navigate])

  return (
    <OnboardingShell step={3}>
      <h1 className="font-headline text-3xl font-extrabold text-on-surface mb-2">
        First assessment in progress
      </h1>
      <p className="text-on-surface-variant mb-8">
        OpenSec is cloning your repo, cross-referencing CVEs, and running
        posture checks. Nothing is written to your repo without your
        explicit approval — every change lands as a draft pull request
        you review.
      </p>

      {assessmentId ? (
        <AssessmentProgressList assessmentId={assessmentId} />
      ) : null}

      {status === 'failed' && (
        <div className="mt-6">
          <InlineErrorCallout
            title="Assessment failed"
            body={
              <>
                Something went wrong during the scan. You can still go to the
                dashboard and retry from there.
              </>
            }
          />
        </div>
      )}

      {isError && (
        <div className="mt-6">
          <InlineErrorCallout
            title="We couldn't read the assessment status"
            body={<>Check the backend logs, then retry from the dashboard.</>}
          />
        </div>
      )}

      <div className="mt-8">
        <WizardNav
          onBack={() => navigate('/onboarding/ai')}
          onNext={() => {
            onboardingStorage.clear()
            navigate('/dashboard')
          }}
          nextLabel={
            status === 'complete' ? 'Go to dashboard' : 'Skip to dashboard'
          }
          nextIcon={status === 'complete' ? 'arrow_forward' : 'skip_next'}
        />
      </div>
    </OnboardingShell>
  )
}
