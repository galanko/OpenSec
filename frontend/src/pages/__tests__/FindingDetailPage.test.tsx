import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router'
import { describe, expect, it } from 'vitest'
import FindingDetailPage from '../FindingDetailPage'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/findings/:id" element={<FindingDetailPage />} />
          <Route path="/findings" element={<div>Findings list</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('<FindingDetailPage />', () => {
  it('renders the plain-language body and technical disclosure', async () => {
    renderAt('/findings/fnd_001')

    await waitFor(() =>
      expect(
        screen.getByRole('heading', {
          name: /pattern-matching library/i,
        }),
      ).toBeInTheDocument(),
    )

    expect(
      screen.getByText(/braces 3\.0\.2 → 3\.0\.3/),
    ).toBeInTheDocument()
    expect(screen.getByText('Technical details')).toBeInTheDocument()
  })

  it('toggles the technical details disclosure', async () => {
    const { container } = renderAt('/findings/fnd_001')
    await waitFor(() =>
      expect(screen.getByText('Technical details')).toBeInTheDocument(),
    )
    const details = container.querySelector('details')!
    expect(details.hasAttribute('open')).toBe(false)
    await userEvent.click(screen.getByText('Technical details'))
    expect(details.hasAttribute('open')).toBe(true)
  })

  it('renders "Back to findings" link', async () => {
    renderAt('/findings/fnd_001')
    await waitFor(() =>
      expect(
        screen.getByRole('link', { name: /back to findings/i }),
      ).toBeInTheDocument(),
    )
  })
})
