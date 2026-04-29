import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { IssueSeverityBadge } from '../IssueSeverityBadge'

describe('IssueSeverityBadge', () => {
  const kinds = ['critical', 'high', 'medium', 'low'] as const

  it.each(kinds)('renders %s with the matching label and accessible name', (kind) => {
    render(<IssueSeverityBadge kind={kind} />)
    const badge = screen.getByLabelText(new RegExp(`severity ${kind}`, 'i'))
    expect(badge).toBeInTheDocument()
    expect(badge.textContent?.toLowerCase()).toContain(kind)
  })

  it.each(kinds)('renders %s in sm size with smaller paddings', (kind) => {
    render(<IssueSeverityBadge kind={kind} size="sm" />)
    const badge = screen.getByLabelText(new RegExp(`severity ${kind}`, 'i'))
    expect(badge).toBeInTheDocument()
    // sm should reduce padding/font compared to md.
    const fontSize = badge.style.fontSize
    expect(fontSize).toBe('10.5px')
  })

  it('applies a stable token-based color for critical (no raw hex)', () => {
    render(<IssueSeverityBadge kind="critical" />)
    const badge = screen.getByLabelText(/severity critical/i)
    // The class list must include a token-based class (e.g. bg-error or
    // text-on-error-container). We just assert the token class appears.
    expect(badge.className).toMatch(/(bg-error|text-on-error-container)/)
  })

  it('uses the warning family for high (matches ADR-0029 token set)', () => {
    render(<IssueSeverityBadge kind="high" />)
    const badge = screen.getByLabelText(/severity high/i)
    expect(badge.className).toMatch(/(warning|warning-container|warning-dim)/)
  })

  it('uses the secondary-container family for medium', () => {
    render(<IssueSeverityBadge kind="medium" />)
    const badge = screen.getByLabelText(/severity medium/i)
    expect(badge.className).toMatch(/secondary-container/)
  })

  it('uses the tertiary-container family for low', () => {
    render(<IssueSeverityBadge kind="low" />)
    const badge = screen.getByLabelText(/severity low/i)
    expect(badge.className).toMatch(/tertiary-container/)
  })

  it('renders the severity icon as a Material Symbols span', () => {
    render(<IssueSeverityBadge kind="critical" />)
    const badge = screen.getByLabelText(/severity critical/i)
    const icon = badge.querySelector('span.material-symbols-outlined')
    expect(icon).not.toBeNull()
    expect(icon?.textContent).toBe('crisis_alert')
  })
})
