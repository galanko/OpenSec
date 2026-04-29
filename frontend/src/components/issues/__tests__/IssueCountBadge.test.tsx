import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { IssueCountBadge } from '../IssueCountBadge'

describe('IssueCountBadge', () => {
  it.each(['primary', 'tertiary', 'muted'] as const)('renders %s tone', (tone) => {
    render(<IssueCountBadge count={3} tone={tone} />)
    const badge = screen.getByTestId(`count-badge-${tone}`)
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).toBe('3')
  })

  it('applies JetBrains Mono via font-mono', () => {
    render(<IssueCountBadge count={9} tone="primary" />)
    expect(screen.getByTestId('count-badge-primary').className).toMatch(/font-mono/)
  })

  it('renders zero counts (does not hide when count is 0)', () => {
    render(<IssueCountBadge count={0} tone="muted" />)
    expect(screen.getByTestId('count-badge-muted').textContent).toBe('0')
  })

  it('matches the prototype min-width and height', () => {
    render(<IssueCountBadge count={42} tone="primary" />)
    const badge = screen.getByTestId('count-badge-primary')
    expect(badge.style.minWidth).toBe('22px')
    expect(badge.style.height).toBe('20px')
  })
})
