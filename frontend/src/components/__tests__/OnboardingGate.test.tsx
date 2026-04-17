import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { server } from '../../mocks/server'
import OnboardingGate from '../OnboardingGate'

interface BootstrapPayload {
  onboarding_completed: boolean
  has_any_assessment: boolean
}

function renderWithRouter(payload: BootstrapPayload) {
  server.use(
    http.get('/api/config/bootstrap', () => HttpResponse.json(payload)),
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

  it('renders wizard when onboarding not completed', async () => {
    renderWithRouter({
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() =>
      expect(screen.getByTestId('wizard')).toBeInTheDocument(),
    )
  })

  it('redirects to /dashboard when onboarding is already completed', async () => {
    renderWithRouter({
      onboarding_completed: true,
      has_any_assessment: true,
    })
    await waitFor(() =>
      expect(screen.getByTestId('dashboard')).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('wizard')).not.toBeInTheDocument()
  })
})
