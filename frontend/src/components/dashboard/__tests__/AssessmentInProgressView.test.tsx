import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AssessmentInProgressView from '@/components/dashboard/AssessmentInProgressView'
import * as dashboardApi from '@/api/dashboard'

function renderView(overrides: Parameters<typeof AssessmentInProgressView>[0]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AssessmentInProgressView {...overrides} />
    </QueryClientProvider>,
  )
}

const PILLS_RUNNING = [
  {
    id: 'trivy',
    label: 'Trivy 0.70',
    version: '0.70.0',
    icon: 'bug_report',
    state: 'active' as const,
    result: null,
  },
  {
    id: 'semgrep',
    label: 'Semgrep',
    version: null,
    icon: 'code',
    state: 'pending' as const,
    result: null,
  },
  {
    id: 'posture',
    label: '15 posture checks',
    version: null,
    icon: 'rule',
    state: 'pending' as const,
    result: null,
  },
]

describe('AssessmentInProgressView', () => {
  // ``vi.spyOn`` does not auto-restore between tests by default; without
  // this, our mocks leak into ``AssessmentProgressList`` and other tests
  // that share ``useAssessmentStatus``.
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders custom headline + description + the step ladder', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: {
        assessment_id: 'asm-1',
        status: 'running',
        progress_pct: 25,
        step: 'cloning',
        steps: [],
        tools: [],
        summary_seen_at: null,
      },
      isError: false,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({
      assessmentId: 'asm-1',
      headline: 'First assessment in progress',
      description: 'A custom narrative for onboarding.',
    })

    expect(
      screen.getByRole('heading', { name: /First assessment in progress/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByText('A custom narrative for onboarding.'),
    ).toBeInTheDocument()
    // The step ladder renders chromeless inside the new view; the steps[]
    // attribute is the wire-shape contract.
    expect(
      screen.getByRole('list', { name: /assessment progress/i }),
    ).toBeInTheDocument()
  })

  it('surfaces the ToolPillBar credit row when tools[] is populated', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: {
        assessment_id: 'asm-2',
        status: 'running',
        progress_pct: 40,
        step: 'looking_up_cves',
        steps: [],
        tools: PILLS_RUNNING,
        summary_seen_at: null,
      },
      isError: false,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({ assessmentId: 'asm-2' })

    await waitFor(() =>
      expect(screen.getByTestId('tool-pill-bar')).toBeInTheDocument(),
    )
    expect(screen.getByTestId('tool-pill-trivy')).toHaveAttribute(
      'data-state',
      'active',
    )
    expect(screen.getByText(/Powered by/)).toBeInTheDocument()
  })

  it('hides the tool-credits row when no tools[] are reported yet', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: {
        assessment_id: 'asm-3',
        status: 'pending',
        progress_pct: 0,
        step: 'cloning',
        steps: [],
        tools: [],
        summary_seen_at: null,
      },
      isError: false,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({ assessmentId: 'asm-3' })

    expect(
      screen.queryByTestId('assessment-progress-tool-credits'),
    ).not.toBeInTheDocument()
  })

  it('renders the failure callout when the assessment fails', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: {
        assessment_id: 'asm-4',
        status: 'failed',
        progress_pct: 0,
        step: null,
        steps: [],
        tools: [],
        summary_seen_at: null,
      },
      isError: false,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({ assessmentId: 'asm-4' })

    expect(screen.getByText(/Assessment failed/i)).toBeInTheDocument()
    const heroIcon = screen.getByTestId('assessment-progress-hero-icon')
    expect(heroIcon).toHaveAttribute('data-status', 'failed')
  })

  it('renders the read-error callout when the status endpoint errors', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: undefined,
      isError: true,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({ assessmentId: 'asm-5' })

    expect(
      screen.getByText(/We couldn't read the assessment status/i),
    ).toBeInTheDocument()
  })

  it('renders the supplied actions slot under the step list', async () => {
    vi.spyOn(dashboardApi, 'useAssessmentStatus').mockReturnValue({
      data: {
        assessment_id: 'asm-6',
        status: 'running',
        progress_pct: 50,
        step: 'checking_posture',
        steps: [],
        tools: [],
        summary_seen_at: null,
      },
      isError: false,
    } as unknown as ReturnType<typeof dashboardApi.useAssessmentStatus>)

    renderView({
      assessmentId: 'asm-6',
      actions: <button>Wizard nav slot</button>,
    })

    expect(
      screen.getByRole('button', { name: 'Wizard nav slot' }),
    ).toBeInTheDocument()
  })
})
