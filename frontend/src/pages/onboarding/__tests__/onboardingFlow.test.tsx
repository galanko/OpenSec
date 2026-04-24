/**
 * Component-level happy path + error path for the onboarding wizard.
 * Exercises all four pages (1.0 → 1.1 → 1.4 → 1.5) against the MSW
 * handlers defined in `src/test/msw/onboardingHandlers.ts`.
 */
import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import Welcome from '@/pages/onboarding/Welcome'
import ConnectRepo from '@/pages/onboarding/ConnectRepo'
import ConfigureAI from '@/pages/onboarding/ConfigureAI'
import StartAssessment from '@/pages/onboarding/StartAssessment'

function renderWizard(initialPath = '/onboarding/welcome') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const router = createMemoryRouter(
    [
      { path: '/onboarding/welcome', element: <Welcome /> },
      { path: '/onboarding/connect', element: <ConnectRepo /> },
      { path: '/onboarding/ai', element: <ConfigureAI /> },
      { path: '/onboarding/start', element: <StartAssessment /> },
      {
        path: '/dashboard',
        element: <div data-testid="dashboard-landed">dashboard</div>,
      },
    ],
    { initialEntries: [initialPath] },
  )
  return render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('onboarding wizard', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('walks the happy path: welcome → connect → ai → start → dashboard', async () => {
    const user = userEvent.setup()
    try {
      renderWizard()

      // 1.0 Welcome
      expect(
        screen.getByRole('heading', { name: /welcome to opensec/i }),
      ).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: /get started/i }))

      // 1.1 Connect repo
      expect(
        await screen.findByRole('heading', { name: /connect your project/i }),
      ).toBeInTheDocument()
      await user.type(
        screen.getByLabelText(/repository url/i),
        'https://github.com/alex-dev/fast-markdown',
      )
      await user.type(
        screen.getByLabelText(/github personal access token/i),
        'ghp_validtoken',
      )
      await user.click(screen.getByRole('button', { name: /verify and continue/i }))

      // 1.3 Verified card appears. Per UX Spec Rev 2 (bug B9), Step 1
      // auto-advances to Step 2 after a ~1.4s dwell with a "Loading step 2…"
      // spinner in place of the old manual "Continue to AI config" button.
      // We wait for the AI-config heading to prove the auto-advance fired —
      // extended timeout because the setTimeout is real, not fake.
      await waitFor(() =>
        expect(screen.getByText('alex-dev/fast-markdown')).toBeInTheDocument(),
      )
      expect(
        await screen.findByText(/loading step 2/i),
      ).toBeInTheDocument()

      // 1.4 Configure AI — pick OpenAI card (default), a model, then type the API key.
      expect(
        await screen.findByRole(
          'heading',
          { name: /configure your ai model/i },
          { timeout: 4_000 },
        ),
      ).toBeInTheDocument()
      await waitFor(() =>
        expect(
          screen.getByRole('option', { name: 'GPT-4o mini' }),
        ).toBeInTheDocument(),
      )
      await user.selectOptions(
        screen.getByLabelText(/^model/i),
        'gpt-4o-mini',
      )
      await user.type(screen.getByLabelText(/api key/i), 'sk-test-key')
      await user.click(
        screen.getByRole('button', { name: /test and continue/i }),
      )

      // 1.5 Start assessment — this screen now shows live progress and
      // auto-advances when the backend reports ``complete``. The test clicks
      // the explicit skip button to stay deterministic.
      expect(
        await screen.findByRole('heading', { name: /first assessment in progress/i }),
      ).toBeInTheDocument()
      await user.click(
        screen.getByRole('button', { name: /skip to dashboard|go to dashboard/i }),
      )

      // Lands on the dashboard.
      expect(await screen.findByTestId('dashboard-landed')).toBeInTheDocument()
    } finally {
      // no-op: real timers throughout
    }
  })

  it('clicking Change on the verified card re-opens the form', async () => {
    const user = userEvent.setup()
    renderWizard('/onboarding/connect')

    await user.type(
      screen.getByLabelText(/repository url/i),
      'https://github.com/alex-dev/fast-markdown',
    )
    await user.type(
      screen.getByLabelText(/github personal access token/i),
      'ghp_validtoken',
    )
    await user.click(
      screen.getByRole('button', { name: /verify and continue/i }),
    )

    await screen.findByText('alex-dev/fast-markdown')
    await user.click(screen.getByRole('button', { name: /change/i }))

    // After Change the form is visible again and the user has NOT advanced.
    expect(
      screen.getByRole('heading', { name: /connect your project/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', { name: /configure your ai model/i }),
    ).not.toBeInTheDocument()
  })

  it('shows the missing-repo-scope error (frame 1.2) and keeps the repo URL', async () => {
    const user = userEvent.setup()
    renderWizard('/onboarding/connect')

    await user.type(
      screen.getByLabelText(/repository url/i),
      'https://github.com/alex-dev/fast-markdown',
    )
    await user.type(
      screen.getByLabelText(/github personal access token/i),
      'no-repo-scope',
    )
    await user.click(
      screen.getByRole('button', { name: /verify and continue/i }),
    )

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/missing the 'repo' scope/i)
    // Repo URL preserved so the user doesn't retype.
    expect(screen.getByLabelText(/repository url/i)).toHaveValue(
      'https://github.com/alex-dev/fast-markdown',
    )
  })

  it('opens the TokenHowToDialog scrim (frame 1.1a) from the help link', async () => {
    const user = userEvent.setup()
    renderWizard('/onboarding/connect')

    await user.click(screen.getByRole('button', { name: /how to create a token/i }))

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(
      screen.getByRole('heading', {
        name: /create a fine-grained github token/i,
      }),
    ).toBeInTheDocument()
    // Deep-link to the real GitHub page for the fine-grained token flow.
    const link = screen.getByRole('link', {
      name: /github\.com\/settings\/personal-access-tokens\/new/i,
    })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
