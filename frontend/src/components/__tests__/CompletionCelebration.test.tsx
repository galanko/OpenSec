import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import CompletionCelebration from '../completion/CompletionCelebration'

function setPrefersReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion: reduce') ? matches : false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

const baseProps = {
  repoName: 'fast-markdown',
  completedDate: '2026-04-14',
  grade: 'A' as const,
  criteriaCount: 5,
  onDownloadClick: vi.fn(),
  onCopyTextClick: vi.fn(),
  onCopyMarkdownClick: vi.fn(),
}

describe('CompletionCelebration', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.clearAllMocks()
  })

  it('announces itself as an assertive status region on mount', () => {
    setPrefersReducedMotion(false)
    render(<CompletionCelebration {...baseProps} />)
    const status = screen.getByRole('status')
    expect(status.getAttribute('aria-live')).toBe('assertive')
  })

  it('renders the spec copy — eyebrow, headline, body', () => {
    setPrefersReducedMotion(false)
    render(<CompletionCelebration {...baseProps} />)
    expect(
      screen.getByText(/Grade A · 5 of 5 criteria met/i),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Security complete/i }),
    ).toBeInTheDocument()
    // Body copy references repo + date verbatim.
    const body = screen.getByText(/reached baseline security/i)
    expect(body.textContent).toMatch(/fast-markdown/)
    expect(body.textContent).toMatch(/2026-04-14/)
  })

  it('shows three calls to action and fires the right callback for each', async () => {
    setPrefersReducedMotion(false)
    const user = userEvent.setup()
    render(<CompletionCelebration {...baseProps} />)

    await user.click(screen.getByRole('button', { name: /Download summary image/i }))
    expect(baseProps.onDownloadClick).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /Copy text summary/i }))
    expect(baseProps.onCopyTextClick).toHaveBeenCalledTimes(1)

    await user.click(screen.getByRole('button', { name: /Copy markdown/i }))
    expect(baseProps.onCopyMarkdownClick).toHaveBeenCalledTimes(1)
  })

  it('renders confetti when motion is allowed', () => {
    setPrefersReducedMotion(false)
    const { container } = render(<CompletionCelebration {...baseProps} />)
    expect(container.querySelectorAll('.confetti').length).toBe(12)
  })

  it('suppresses confetti under prefers-reduced-motion', () => {
    setPrefersReducedMotion(true)
    const { container } = render(<CompletionCelebration {...baseProps} />)
    expect(container.querySelectorAll('.confetti').length).toBe(0)
  })

  it('is not a dialog — no focus trap, no role=dialog', () => {
    setPrefersReducedMotion(false)
    render(<CompletionCelebration {...baseProps} />)
    // By design, this is a role=status announcement region, not a modal.
    // A future refactor to role=alertdialog would break the a11y contract.
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.queryByRole('alertdialog')).toBeNull()
  })
})
