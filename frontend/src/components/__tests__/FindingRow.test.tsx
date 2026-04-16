import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Finding } from '@/api/client'
import FindingRow from '../FindingRow'

const baseFinding: Finding = {
  id: 'f1',
  source_type: 'osv',
  source_id: 'CVE-2024-4067',
  title: 'A pattern-matching library your project uses has a known flaw',
  description: 'Long technical description.',
  plain_description:
    'The braces npm package can be tricked into infinite loops. Bump braces 3.0.2 → 3.0.3.',
  raw_severity: 'critical',
  normalized_priority: 'critical',
  asset_id: 'pkg_braces',
  asset_label: 'braces@3.0.2',
  status: 'new',
  likely_owner: null,
  why_this_matters: null,
  raw_payload: {
    cve: 'CVE-2024-4067',
    cvss_score: 7.5,
    attack_vector: 'regex denial-of-service',
  },
  created_at: '2026-04-16T08:30:00Z',
  updated_at: '2026-04-16T09:00:00Z',
}

describe('<FindingRow />', () => {
  it('leads with the plain-language title', () => {
    render(<FindingRow finding={baseFinding} onSolve={() => {}} />)
    expect(
      screen.getByRole('heading', {
        name: /pattern-matching library/i,
      }),
    ).toBeInTheDocument()
  })

  it('prefers plain_description over raw description', () => {
    render(<FindingRow finding={baseFinding} onSolve={() => {}} />)
    expect(screen.getByText(/infinite loops/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/Long technical description/i),
    ).not.toBeInTheDocument()
  })

  it('renders a monospace tech line with source_id and CVSS', () => {
    render(<FindingRow finding={baseFinding} onSolve={() => {}} />)
    const techLine = screen.getByTestId('finding-tech-line')
    expect(techLine).toHaveClass(/font-mono/)
    expect(techLine.textContent).toMatch(/CVE-2024-4067/)
    expect(techLine.textContent).toMatch(/7\.5/)
  })

  it('falls back to description when plain_description is absent', () => {
    render(
      <FindingRow
        finding={{ ...baseFinding, plain_description: null }}
        onSolve={() => {}}
      />,
    )
    expect(
      screen.getByText(/Long technical description/i),
    ).toBeInTheDocument()
  })

  it('invokes onSolve when Solve is clicked', async () => {
    const onSolve = vi.fn()
    render(<FindingRow finding={baseFinding} onSolve={onSolve} />)
    await userEvent.click(screen.getByRole('button', { name: /solve/i }))
    expect(onSolve).toHaveBeenCalledWith(baseFinding)
  })
})
