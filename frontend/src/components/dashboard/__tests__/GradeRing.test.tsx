import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import GradeRing from '../GradeRing'

describe('<GradeRing />', () => {
  it('renders the letter grade in the center', () => {
    render(<GradeRing grade="C" criteriaMet={3} criteriaTotal={5} />)
    expect(screen.getByTestId('grade-letter')).toHaveTextContent('C')
  })

  it('renders the "X of Y" caption', () => {
    render(<GradeRing grade="C" criteriaMet={3} criteriaTotal={5} />)
    expect(screen.getByText(/3 of 5/i)).toBeInTheDocument()
  })

  it('sets a conic-gradient background with the filled arc matching criteria ratio', () => {
    render(<GradeRing grade="C" criteriaMet={3} criteriaTotal={5} />)
    const ring = screen.getByTestId('grade-ring')
    const style = ring.getAttribute('style') ?? ''
    // 3/5 = 60% → 216deg
    expect(style).toMatch(/216deg/)
    expect(style).toMatch(/conic-gradient/)
  })

  it('renders a dash when grade is null (assessment running)', () => {
    render(<GradeRing grade={null} criteriaMet={0} criteriaTotal={5} />)
    expect(screen.getByTestId('grade-letter')).toHaveTextContent('—')
  })
})
