import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ScorecardInfoLine from '../dashboard/ScorecardInfoLine'

describe('ScorecardInfoLine (placeholder)', () => {
  it('renders the default scorecard URL', () => {
    render(<ScorecardInfoLine />)
    expect(screen.getByTestId('ScorecardInfoLine')).toBeInTheDocument()
    expect(screen.getByText('https://github.com/ossf/scorecard')).toBeInTheDocument()
  })

  it('renders a custom URL when passed', () => {
    render(<ScorecardInfoLine scorecardUrl="https://example.test" />)
    expect(screen.getByText('https://example.test')).toBeInTheDocument()
  })
})
