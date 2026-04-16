import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { server } from '../../mocks/server'
import FirstRunRedirect from '../FirstRunRedirect'

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
        path: '/',
        element: (
          <FirstRunRedirect>
            <div data-testid="home">findings home</div>
          </FirstRunRedirect>
        ),
      },
      {
        path: '/onboarding/welcome',
        element: <div data-testid="welcome">onboarding welcome</div>,
      },
    ],
    { initialEntries: ['/'] },
  )
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('<FirstRunRedirect />', () => {
  afterEach(() => server.resetHandlers())

  it('redirects to onboarding when flag is on and neither signal is set', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() =>
      expect(screen.getByTestId('welcome')).toBeInTheDocument(),
    )
  })

  it('renders children when the flag is off', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: false,
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() => expect(screen.getByTestId('home')).toBeInTheDocument())
  })

  it('renders children when onboarding is already completed', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: true,
      has_any_assessment: false,
    })
    await waitFor(() => expect(screen.getByTestId('home')).toBeInTheDocument())
  })

  it('renders children when an assessment already exists', async () => {
    renderWithRouter({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: false,
      has_any_assessment: true,
    })
    await waitFor(() => expect(screen.getByTestId('home')).toBeInTheDocument())
  })
})
