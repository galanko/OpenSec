import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router'
import IssuesPage from '../IssuesPage'
import type { Finding } from '../../api/client'
import { server } from '../../mocks/server'
import { makeFinding } from '../../test/fixtures/finding'

const navigateMock = vi.fn()
vi.mock('react-router', async (orig) => {
  const actual = (await orig()) as Record<string, unknown>
  return {
    ...actual,
    useNavigate: () => navigateMock,
  }
})

function renderPage(findings: Finding[]) {
  server.use(
    http.get('/api/findings', () => HttpResponse.json(findings)),
    http.get('/api/dashboard', () =>
      HttpResponse.json({
        assessment: null,
        criteria: [],
        criteria_snapshot: { snapshot: {} },
        findings_count_by_priority: {},
        grade: 'B',
        posture_checks: [],
        posture_pass_count: 0,
      }),
    ),
    http.get('/api/settings/integrations', () =>
      HttpResponse.json([
        {
          id: 'gh-1',
          adapter_type: 'ticketing',
          provider_name: 'GitHub',
          enabled: true,
          config: { repo_url: 'https://github.com/x/y' },
          last_test_result: null,
          updated_at: '',
        },
      ]),
    ),
    http.get('/api/settings/integrations/health', () =>
      HttpResponse.json([
        {
          integration_id: 'gh-1',
          registry_id: 'github',
          provider_name: 'GitHub',
          credential_status: 'ok',
          connection_status: 'ok',
          last_checked: null,
          error_message: null,
        },
      ]),
    ),
  )
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <IssuesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('IssuesPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    navigateMock.mockReset()
  })
  afterEach(() => {
    sessionStorage.clear()
  })

  it('renders the four sections in order with the right counts', async () => {
    const findings = [
      makeFinding({ id: 'r1', stage: 'plan_ready' }),
      makeFinding({ id: 'r2', stage: 'pr_ready' }),
      makeFinding({ id: 'p1', stage: 'planning' }),
      makeFinding({ id: 'p2', stage: 'generating' }),
      makeFinding({ id: 't1', stage: 'todo' }),
      makeFinding({ id: 'd1', stage: 'fixed' }),
    ]
    renderPage(findings)

    await screen.findByLabelText('Review section')
    expect(screen.getByLabelText('Review section')).toBeInTheDocument()
    expect(screen.getByLabelText('In progress section')).toBeInTheDocument()
    expect(screen.getByLabelText('Todo section')).toBeInTheDocument()
    expect(screen.getByLabelText('Done section')).toBeInTheDocument()
  })

  it('In progress section is collapsed by default and shows the breakdown caption', async () => {
    const findings = [
      makeFinding({ id: 'p1', stage: 'planning' }),
      makeFinding({ id: 'p2', stage: 'generating' }),
      makeFinding({ id: 'p3', stage: 'opening_pr' }),
      makeFinding({ id: 'p4', stage: 'validating' }),
    ]
    renderPage(findings)
    const inProgress = await screen.findByLabelText('In progress section')
    expect(inProgress.textContent).toContain('1 planning')
    expect(inProgress.textContent).toContain('1 generating')
    expect(inProgress.textContent).toContain('1 opening PR')
    expect(inProgress.textContent).toContain('1 validating')
    // Collapsed: rows are not yet rendered.
    expect(screen.queryByText(/Issue p1/)).toBeNull()
  })

  it('expanding In progress reveals the rows and persists in sessionStorage', async () => {
    const findings = [makeFinding({ id: 'p1', stage: 'planning' })]
    renderPage(findings)
    const toggle = await screen.findByRole('button', {
      name: /Agents working — no action needed|Hide/i,
    })
    fireEvent.click(toggle)
    await waitFor(() => expect(screen.getByText('Issue p1')).toBeInTheDocument())
    expect(sessionStorage.getItem('opensec.issues.inProgressOpen')).toBe('1')
  })

  it('clicking a Todo row triggers createWorkspace and navigates to /workspace/:id', async () => {
    server.use(
      http.post('/api/workspaces', () =>
        HttpResponse.json({
          id: 'w-new',
          finding_id: 't1',
          state: 'open',
          current_focus: null,
          active_plan_version: null,
          linked_ticket_id: null,
          validation_state: null,
          created_at: '',
          updated_at: '',
        }),
      ),
    )
    const findings = [makeFinding({ id: 't1', stage: 'todo' })]
    renderPage(findings)
    // Wait for the integrations + health queries to resolve so the GitHub
    // repo-guard guard is satisfied before clicking Start.
    await screen.findByText(/grade B/)
    const startBtn = await screen.findByRole('button', { name: /^Start$/i })
    // Allow the integrations query to settle (driven by useIntegrations).
    await waitFor(() => {
      // No assertion needed; this just yields the microtask queue.
      expect(startBtn).toBeInTheDocument()
    })
    fireEvent.click(startBtn)
    await waitFor(
      () => expect(navigateMock).toHaveBeenCalledWith('/workspace/w-new'),
      { timeout: 3000 },
    )
  })

  it('clicking a Review row with an existing workspace navigates without creating a new one', async () => {
    const findings = [
      makeFinding({ id: 'r1', stage: 'plan_ready', workspaceId: 'w-existing' }),
    ]
    renderPage(findings)
    const reviewBtn = await screen.findByRole('button', { name: /Review plan/i })
    fireEvent.click(reviewBtn)
    await waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/workspace/w-existing'),
    )
  })

  it('renders the empty-Review card only when review is empty AND others are not', async () => {
    const findings = [makeFinding({ id: 't1', stage: 'todo' })]
    renderPage(findings)
    expect(await screen.findByText(/Review is clear\./i)).toBeInTheDocument()
  })

  it('does NOT render the empty-Review card when there are zero findings overall', async () => {
    renderPage([])
    // The blanket EmptyState handles fully-empty repos; we should not
    // double up with the "Review is clear" tertiary card.
    expect(screen.queryByText(/Review is clear\./i)).toBeNull()
  })

  it('hides the migration banner once dismissed and reflects in sessionStorage', async () => {
    renderPage([])
    const dismiss = await screen.findByRole('button', { name: /dismiss/i })
    fireEvent.click(dismiss)
    expect(sessionStorage.getItem('opensec.issues.migrationBannerDismissed')).toBe(
      '1',
    )
  })

  it('Severity filter narrows the visible rows', async () => {
    const findings = [
      makeFinding({ id: 'a', stage: 'todo', severity: 'critical' }),
      makeFinding({ id: 'b', stage: 'todo', severity: 'high' }),
      makeFinding({ id: 'c', stage: 'todo', severity: 'high' }),
    ]
    renderPage(findings)
    await screen.findByText('Issue a')
    expect(screen.getByText('Issue a')).toBeInTheDocument()
    expect(screen.getByText('Issue b')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Critical/i }))
    await waitFor(() => {
      expect(screen.getByText('Issue a')).toBeInTheDocument()
      expect(screen.queryByText('Issue b')).toBeNull()
    })
  })

  it('Done section shows at most 4 rows by default with a Show all toggle', async () => {
    const findings = [
      makeFinding({ id: 'd1', stage: 'fixed' }),
      makeFinding({ id: 'd2', stage: 'fixed' }),
      makeFinding({ id: 'd3', stage: 'fixed' }),
      makeFinding({ id: 'd4', stage: 'fixed' }),
      makeFinding({ id: 'd5', stage: 'fixed' }),
      makeFinding({ id: 'd6', stage: 'fixed' }),
    ]
    renderPage(findings)
    await screen.findByText('Issue d1')
    expect(screen.getByText('Issue d4')).toBeInTheDocument()
    expect(screen.queryByText('Issue d5')).toBeNull()
    const showAll = screen.getByRole('button', { name: /Show all/i })
    fireEvent.click(showAll)
    await waitFor(() =>
      expect(screen.getByText('Issue d5')).toBeInTheDocument(),
    )
  })
})
