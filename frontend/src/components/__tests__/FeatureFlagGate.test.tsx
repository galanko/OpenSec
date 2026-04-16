import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { server } from '../../mocks/server'
import FeatureFlagGate from '../FeatureFlagGate'

function renderWithRouter(initial = '/onboarding/welcome') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const router = createMemoryRouter(
    [
      {
        path: '/onboarding/welcome',
        element: (
          <FeatureFlagGate flag="v1_1_from_zero_to_secure_enabled">
            <div data-testid="wizard">wizard content</div>
          </FeatureFlagGate>
        ),
      },
      {
        path: '/findings',
        element: <div data-testid="findings">findings home</div>,
      },
    ],
    { initialEntries: [initial] },
  )
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('<FeatureFlagGate />', () => {
  afterEach(() => server.resetHandlers())

  it('redirects to the legacy home when the flag is off', async () => {
    server.use(
      http.get('/api/config/feature-flags', () =>
        HttpResponse.json({ v1_1_from_zero_to_secure_enabled: false }),
      ),
    )
    renderWithRouter()
    await waitFor(() =>
      expect(screen.getByTestId('findings')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('wizard')).not.toBeInTheDocument()
  })

  it('renders children when the flag is on', async () => {
    server.use(
      http.get('/api/config/feature-flags', () =>
        HttpResponse.json({ v1_1_from_zero_to_secure_enabled: true }),
      ),
    )
    renderWithRouter()
    await waitFor(() =>
      expect(screen.getByTestId('wizard')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('findings')).not.toBeInTheDocument()
  })

  it('redirects when the config endpoint errors (fail-closed)', async () => {
    server.use(
      http.get('/api/config/feature-flags', () =>
        HttpResponse.json({ detail: 'boom' }, { status: 500 }),
      ),
    )
    renderWithRouter()
    await waitFor(() =>
      expect(screen.getByTestId('findings')).toBeInTheDocument(),
    )
  })
})
