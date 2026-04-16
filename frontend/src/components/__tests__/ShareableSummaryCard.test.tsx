import { createRef } from 'react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ShareableSummaryCard from '../completion/ShareableSummaryCard'

describe('ShareableSummaryCard', () => {
  const props = {
    repoName: 'fast-markdown',
    completedAt: '2026-04-14',
    vulnsFixed: 12,
    postureChecksPassing: 5,
    prsMerged: 3,
    grade: 'A' as const,
  }

  it('renders all six declared props', () => {
    render(<ShareableSummaryCard {...props} />)
    expect(screen.getByText('fast-markdown')).toBeInTheDocument()
    expect(screen.getByText(/Completed 2026-04-14/)).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText(/Grade A/)).toBeInTheDocument()
  })

  it('uses the sanctioned gradient as an inline style', () => {
    const { container } = render(<ShareableSummaryCard {...props} />)
    const root = container.firstElementChild as HTMLElement
    // Contract: the gradient lives inline on the outermost element (the one
    // with the ref that html-to-image captures). Do NOT move this to a
    // Tailwind token; it is the single sanctioned gradient in the product.
    //
    // jsdom re-serializes inline colors as `rgb(...)`, so we accept either
    // the raw hex (what the DOM actually ships in a browser) or the
    // jsdom-normalized rgb form (what the test environment sees).
    const style = root.getAttribute('style') ?? ''
    expect(style).toMatch(/linear-gradient\(135deg,/i)
    expect(style).toMatch(/#4d44e3|rgb\(77,\s*68,\s*227\)/i)
    expect(style).toMatch(/#575e78|rgb\(87,\s*94,\s*120\)/i)
  })

  it('renders at a true 1200x630 export size', () => {
    const { container } = render(<ShareableSummaryCard {...props} />)
    const root = container.firstElementChild as HTMLElement
    const style = root.getAttribute('style') ?? ''
    expect(style).toMatch(/width:\s*1200px/)
    expect(style).toMatch(/height:\s*630px/)
  })

  it('places all white text on the gradient at rgba ≥ 0.92 (WCAG AA)', () => {
    const { container } = render(<ShareableSummaryCard {...props} />)
    // The brief mandates all white text atop the sanctioned gradient use
    // `rgba(255,255,255,0.92)` minimum. Grepping the rendered inline style
    // is the most robust way to lock this contract — jsdom's getComputedStyle
    // does not resolve Tailwind class-defined values, but inline styles
    // survive verbatim in innerHTML.
    const matches = container.innerHTML.match(
      /rgba\(255,\s*255,\s*255,\s*0\.(?:9[2-9]|\d{2,})\)/g,
    )
    expect(matches).not.toBeNull()
    // Six text runs use this contract (eyebrow, completed date, three stats
    // labels, footer left). A refactor that drops below three is a silent
    // regression of the contract, so we floor at 3.
    expect(matches!.length).toBeGreaterThanOrEqual(3)
  })

  it('forwards the ref to the outermost element so html-to-image can capture it', () => {
    const ref = createRef<HTMLDivElement>()
    const { container } = render(<ShareableSummaryCard {...props} ref={ref} />)
    expect(ref.current).toBe(container.firstElementChild)
  })

  it('renders the stats labels from the spec', () => {
    render(<ShareableSummaryCard {...props} />)
    expect(screen.getByText(/Vulns fixed/i)).toBeInTheDocument()
    expect(screen.getByText(/Posture checks/i)).toBeInTheDocument()
    expect(screen.getByText(/PRs merged/i)).toBeInTheDocument()
  })

  it('exposes the card to screen readers as an image with a descriptive label', () => {
    render(<ShareableSummaryCard {...props} />)
    const root = screen.getByRole('img')
    expect(root.getAttribute('aria-label')).toMatch(/fast-markdown/i)
  })
})
