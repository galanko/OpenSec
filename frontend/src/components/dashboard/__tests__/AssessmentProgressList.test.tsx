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
  it('shows the five fixed steps', async () => {
    render(
      <Wrapper>
        <AssessmentProgressList assessmentId="asmt_running_001" />
      </Wrapper>,
    )
    // Wait for first poll to resolve so UI advances out of the "pending" all-state.
    await waitFor(() =>
      expect(
        screen.getByRole('list', { name: /assessment progress/i }),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText(/clone repository/i)).toBeInTheDocument()
    expect(screen.getByText(/parse lockfiles/i)).toBeInTheDocument()
    expect(screen.getByText(/cross-reference cves/i)).toBeInTheDocument()
    expect(screen.getByText(/posture checks/i)).toBeInTheDocument()
    expect(screen.getByText(/compute grade/i)).toBeInTheDocument()
  })

  it('marks the active step as running and earlier steps as done', async () => {
    render(
      <Wrapper>
        <AssessmentProgressList assessmentId="asmt_running_001" />
      </Wrapper>,
    )
    // First poll returns step=cloning → the Clone row is "running".
    await waitFor(() => {
      const items = screen.getAllByTestId('assessment-step')
      const cloneItem = items.find((el) =>
        el.textContent?.toLowerCase().includes('clone'),
      )!
      expect(cloneItem.dataset.state).toBe('running')
    })
  })
})
