import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { server } from '../../mocks/server'
import FirstRunRedirect from '../FirstRunRedirect'

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

  it('redirects to onboarding on a fresh DB (both signals false)', async () => {
    renderWithRouter({
      onboarding_completed: false,
      has_any_assessment: false,
    })
    await waitFor(() =>
      expect(screen.getByTestId('welcome')).toBeInTheDocument(),
    )
  })

  it('renders children when onboarding is already completed', async () => {
    renderWithRouter({
      onboarding_completed: true,
      has_any_assessment: false,
    })
    await waitFor(() => expect(screen.getByTestId('home')).toBeInTheDocument())
  })

  it('renders children when an assessment already exists', async () => {
    renderWithRouter({
      onboarding_completed: false,
      has_any_assessment: true,
    })
    await waitFor(() => expect(screen.getByTestId('home')).toBeInTheDocument())
  })
})
