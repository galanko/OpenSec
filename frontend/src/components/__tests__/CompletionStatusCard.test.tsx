import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import CompletionStatusCard from '../completion/CompletionStatusCard'

describe('CompletionStatusCard', () => {
  const baseProps = {
    completionId: 'c-123',
    completedAt: '2026-04-02T12:00:00Z',
  }

  it('renders the "Security complete" eyebrow', () => {
    render(<CompletionStatusCard {...baseProps} />)
    expect(screen.getByText(/Security complete/i)).toBeInTheDocument()
  })

  it('renders the shield as a real button with the correct aria-label', () => {
    render(<CompletionStatusCard {...baseProps} onReopenSummary={() => {}} />)
    const btn = screen.getByRole('button', {
      name: /Re-open shareable summary card/i,
    })
    expect(btn.tagName).toBe('BUTTON')
    expect(btn.getAttribute('type')).toBe('button')
  })

  it('renders the "Tap for summary" micro-label as aria-hidden', () => {
    render(<CompletionStatusCard {...baseProps} />)
    const micro = screen.getByText(/Tap for summary/i)
    expect(micro.getAttribute('aria-hidden')).toBe('true')
  })

  it('fires onReopenSummary on click', async () => {
    const onReopen = vi.fn()
    const user = userEvent.setup()
    render(<CompletionStatusCard {...baseProps} onReopenSummary={onReopen} />)

    await user.click(
      screen.getByRole('button', { name: /Re-open shareable summary card/i }),
    )
    expect(onReopen).toHaveBeenCalledTimes(1)
  })

  it('fires onReopenSummary on Enter key', async () => {
    const onReopen = vi.fn()
    const user = userEvent.setup()
    render(<CompletionStatusCard {...baseProps} onReopenSummary={onReopen} />)

    const btn = screen.getByRole('button', {
      name: /Re-open shareable summary card/i,
    })
    btn.focus()
    await user.keyboard('{Enter}')
    expect(onReopen).toHaveBeenCalledTimes(1)
  })

  it('fires onReopenSummary on Space key', async () => {
    const onReopen = vi.fn()
    const user = userEvent.setup()
    render(<CompletionStatusCard {...baseProps} onReopenSummary={onReopen} />)

    const btn = screen.getByRole('button', {
      name: /Re-open shareable summary card/i,
    })
    btn.focus()
    await user.keyboard(' ')
    expect(onReopen).toHaveBeenCalledTimes(1)
  })

  it('survives null completionId and null completedAt gracefully', () => {
    render(
      <CompletionStatusCard completionId={null} completedAt={null} />,
    )
    // Even without a date, the eyebrow still renders — the button is the
    // only required interaction.
    expect(screen.getByText(/Security complete/i)).toBeInTheDocument()
  })

  it('carries the focus-visible ring class (keyboard affordance)', () => {
    render(<CompletionStatusCard {...baseProps} />)
    const btn = screen.getByRole('button', {
      name: /Re-open shareable summary card/i,
    })
    expect(btn.className).toMatch(/focus-visible:ring-2/)
    expect(btn.className).toMatch(/ring-primary\/40/)
  })

  it('is a no-op when onReopenSummary is not provided', async () => {
    const user = userEvent.setup()
    render(<CompletionStatusCard {...baseProps} />)
    // No prop given — clicking should not throw.
    await user.click(
      screen.getByRole('button', { name: /Re-open shareable summary card/i }),
    )
    // If we got here without throwing, the card handled the absent callback.
    expect(true).toBe(true)
  })
})
