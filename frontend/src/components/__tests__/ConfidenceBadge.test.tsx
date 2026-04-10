import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ConfidenceBadge from '../ConfidenceBadge'

describe('ConfidenceBadge', () => {
  it('renders high confidence for score >= 0.7', () => {
    render(<ConfidenceBadge confidence={0.85} />)
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('\u25CF\u25CF\u25CF\u25CF')).toBeInTheDocument()
  })

  it('renders medium confidence for score 0.4-0.69', () => {
    render(<ConfidenceBadge confidence={0.5} />)
    expect(screen.getByText('Medium')).toBeInTheDocument()
    expect(screen.getByText('\u25CF\u25CF\u25CB\u25CB')).toBeInTheDocument()
  })

  it('renders low confidence for score < 0.4', () => {
    render(<ConfidenceBadge confidence={0.2} />)
    expect(screen.getByText('Low')).toBeInTheDocument()
    expect(screen.getByText('\u25CF\u25CB\u25CB\u25CB')).toBeInTheDocument()
  })

  it('renders nothing for null confidence', () => {
    const { container } = render(<ConfidenceBadge confidence={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders nothing for undefined confidence', () => {
    const { container } = render(<ConfidenceBadge confidence={undefined} />)
    expect(container.innerHTML).toBe('')
  })

  it('treats 0.7 as high (boundary)', () => {
    render(<ConfidenceBadge confidence={0.7} />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('treats 0.4 as medium (boundary)', () => {
    render(<ConfidenceBadge confidence={0.4} />)
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })
})
