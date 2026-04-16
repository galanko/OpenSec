/**
 * Component-level happy path + error path for the onboarding wizard.
 * Exercises all four pages (1.0 → 1.1 → 1.4 → 1.5) against the MSW
 * handlers defined in `src/test/msw/onboardingHandlers.ts`.
 */
import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'

import Welcome from '@/pages/onboarding/Welcome'
import ConnectRepo from '@/pages/onboarding/ConnectRepo'
import ConfigureAI from '@/pages/onboarding/ConfigureAI'
import StartAssessment from '@/pages/onboarding/StartAssessment'

function renderWizard(initialPath = '/onboarding/welcome') {
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
  return render(<RouterProvider router={router} />)
}

describe('onboarding wizard', () => {
  it('walks the happy path: welcome → connect → ai → start → dashboard', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
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

      // 1.3 Verified card appears, then auto-advances to 1.4. The wait
      // exceeds the page's VERIFIED_AUTO_ADVANCE_MS constant (1200 ms).
      await waitFor(() =>
        expect(screen.getByText('alex-dev/fast-markdown')).toBeInTheDocument(),
      )
      vi.advanceTimersByTime(2000)

      // 1.4 Configure AI
      expect(
        await screen.findByRole('heading', { name: /configure your ai model/i }),
      ).toBeInTheDocument()
      await user.type(screen.getByLabelText(/api key/i), 'sk-test-key')
      await user.click(
        screen.getByRole('button', { name: /test and continue/i }),
      )

      // 1.5 Start assessment
      expect(
        await screen.findByRole('heading', { name: /ready to assess/i }),
      ).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: /start assessment/i }))

      // Lands on the dashboard.
      expect(await screen.findByTestId('dashboard-landed')).toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })

  it('clicking Change during the verified window cancels the auto-advance', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    try {
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

      // 1.3 verified card is visible — back out before the 1.2s auto-advance.
      await screen.findByText('alex-dev/fast-markdown')
      await user.click(screen.getByRole('button', { name: /change/i }))

      // Advance well past the auto-advance window: we should still be on
      // ConnectRepo (the form has re-rendered), NOT on ConfigureAI.
      vi.advanceTimersByTime(5000)
      expect(
        screen.getByRole('heading', { name: /connect your project/i }),
      ).toBeInTheDocument()
      expect(
        screen.queryByRole('heading', { name: /configure your ai model/i }),
      ).not.toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
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
        name: /create a github personal access token/i,
      }),
    ).toBeInTheDocument()
    // Deep-link to the real GitHub page.
    const link = screen.getByRole('link', { name: /github\.com\/settings\/tokens/i })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
