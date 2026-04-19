import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CriteriaMeter from '../CriteriaMeter'

describe('<CriteriaMeter />', () => {
  it('renders "total" pills, filling "met" from the left', () => {
    render(<CriteriaMeter met={3} total={5} />)
    const pills = screen.getAllByTestId('criteria-meter-pill')
    expect(pills).toHaveLength(5)
    expect(pills.slice(0, 3).every((p) => p.dataset.state === 'met')).toBe(
      true,
    )
    expect(pills.slice(3).every((p) => p.dataset.state === 'empty')).toBe(
      true,
    )
  })

  it('clamps met to total', () => {
    render(<CriteriaMeter met={9} total={5} />)
    const pills = screen.getAllByTestId('criteria-meter-pill')
    expect(pills.filter((p) => p.dataset.state === 'met')).toHaveLength(5)
  })
})
