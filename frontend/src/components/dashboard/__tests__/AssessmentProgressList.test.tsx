import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import AssessmentProgressList from '../AssessmentProgressList'

function Wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe('<AssessmentProgressList />', () => {
  it('renders the v0.2 six-step ladder from the wire shape', async () => {
    render(
      <Wrapper>
        <AssessmentProgressList assessmentId="asmt_running_001" />
      </Wrapper>,
    )
    // Wait for the first poll to resolve and ship the v0.2 steps[] from the
    // wire shape — without this the assertion races the network mock and
    // sees the "Waiting for the engine…" placeholder.
    await waitFor(() =>
      expect(
        screen.getByText(/Detecting project type/i),
      ).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/Scanning dependencies with Trivy/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Scanning for secrets with Trivy/i),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Scanning code with Semgrep/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/Checking repo posture/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Generating plain-language descriptions/i),
    ).toBeInTheDocument()
  })

  it('marks the active step as running and earlier steps as done', async () => {
    render(
      <Wrapper>
        <AssessmentProgressList assessmentId="asmt_running_001" />
      </Wrapper>,
    )
    // First poll returns step='detect' → that row is "running" and the
    // earlier rows would be done (none, since detect is first). We assert
    // the running cursor on the first row.
    await waitFor(() => {
      const items = screen.getAllByTestId('assessment-step')
      const detectRow = items.find((el) =>
        el.textContent?.toLowerCase().includes('detecting project type'),
      )!
      expect(detectRow.dataset.state).toBe('running')
    })
  })
})
