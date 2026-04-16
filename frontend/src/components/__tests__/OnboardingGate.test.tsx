import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { server } from '../../mocks/server'
import OnboardingGate from '../OnboardingGate'

interface FlagPayload {
  v1_1_from_zero_to_secure_enabled: boolean
  onboarding_completed: boolean
  has_any_assessment: boolean
}

function renderWithRouter(flags: FlagPayload) {
  server.use(
    http.get('/api/config/feature-flags', () => HttpResponse.json(flags)),
  )
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const router = createMemoryRouter(
    [
      {
        path: '/onboarding/welcome',
        element: (
          <OnboardingGate>
            <div data-testid="wizard">wizard</div>
          </OnboardingGate>
        ),
      },
      { path: '/findings', element: <div data-testid="findings">findings</div> },
      {
        path: '/dashboard',
        element: <div data-testid="dashboard">dashboard</div>,
      },
    ],
    { initialEntries: ['/onboarding/welcome'] },
  )
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('<OnboardingGate />', () => {
  afterEach(() => server.resetHandlers())

  it('renders wizard when flag is on and onboarding not completed', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() =>
      expect(screen.getByTestId('wizard')).toBeInTheDocument(),
    )
  })

  it('redirects to /findings when the flag is off', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: false,
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() =>
      expect(screen.getByTestId('findings')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('wizard')).not.toBeInTheDocument()
  })

  it('redirects to /dashboard when onboarding is already completed', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: true,
      has_any_assessment: true,
    })
    await waitFor(() =>
      expect(screen.getByTestId('dashboard')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('wizard')).not.toBeInTheDocument()
  })
})
