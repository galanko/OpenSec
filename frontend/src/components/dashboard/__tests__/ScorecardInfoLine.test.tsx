import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ScorecardInfoLine from '../ScorecardInfoLine'

describe('<ScorecardInfoLine />', () => {
  it('renders the "second opinion" copy and learn-more link', () => {
    render(<ScorecardInfoLine />)
    expect(
      screen.getByText(/second opinion/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /learn more/i })).toBeInTheDocument()
  })

  it('external link MUST have target="_blank" and rel="noopener noreferrer"', () => {
    render(<ScorecardInfoLine />)
    const link = screen.getByRole('link', { name: /learn more/i })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    expect(link.getAttribute('href')).toMatch(/ossf\/scorecard/)
  })

  it('respects a custom scorecardUrl prop', () => {
    render(<ScorecardInfoLine scorecardUrl="https://example.com/audit" />)
    const link = screen.getByRole('link', { name: /learn more/i })
    expect(link).toHaveAttribute('href', 'https://example.com/audit')
  })
})
