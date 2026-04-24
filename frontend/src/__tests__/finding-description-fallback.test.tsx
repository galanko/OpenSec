/**
 * PRD-0004 Story 5 / IMPL-0004 T13 — description fallback on finding cards.
 *
 * Three-branch matrix tested at the component boundary (FindingRow):
 *   1. plain_description present → render plain, no note
 *   2. plain_description empty / description present → render description +
 *      DescriptionFallbackNote
 *   3. both empty → empty-state line with "No description available"
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'
import type { Finding } from '@/api/client'
import FindingRow from '@/components/FindingRow'
import { resolveFindingDescription } from '@/lib/findingDescription'

function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 'f1',
    source_type: 'trivy',
    source_id: 'CVE-2024-1234',
    title: 'Example CVE',
    description: null,
    plain_description: null,
    raw_severity: 'medium',
    normalized_priority: 'medium',
    asset_id: null,
    asset_label: 'api-server',
    status: 'new',
    likely_owner: null,
    why_this_matters: null,
    raw_payload: null,
    created_at: '2026-04-24T00:00:00Z',
    updated_at: '2026-04-24T00:00:00Z',
    ...overrides,
  } as Finding
}

function renderRow(finding: Finding) {
  return render(
    <MemoryRouter>
      <FindingRow finding={finding} onSolve={vi.fn()} />
    </MemoryRouter>,
  )
}

describe('resolveFindingDescription()', () => {
  it('prefers plain_description when non-empty', () => {
    expect(
      resolveFindingDescription('plain', 'raw'),
    ).toEqual({ kind: 'plain', text: 'plain' })
  })

  it('falls back to description when plain is missing or whitespace', () => {
    expect(
      resolveFindingDescription(null, 'raw scanner text'),
    ).toEqual({ kind: 'fallback', text: 'raw scanner text' })
    expect(
      resolveFindingDescription('   ', 'raw scanner text'),
    ).toEqual({ kind: 'fallback', text: 'raw scanner text' })
  })

  it('returns empty when both are missing', () => {
    expect(resolveFindingDescription(null, null)).toEqual({ kind: 'empty' })
    expect(resolveFindingDescription('', '')).toEqual({ kind: 'empty' })
  })
})

describe('<FindingRow /> description fallback', () => {
  it('renders plain_description without the fallback note', () => {
    const finding = makeFinding({
      plain_description: 'Clear plain-English summary.',
      description: 'Raw scanner blob that should not appear.',
    })
    renderRow(finding)

    expect(screen.getByTestId('finding-description')).toHaveTextContent(
      'Clear plain-English summary.',
    )
    expect(
      screen.queryByTestId('description-fallback-note'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByTestId('finding-description-empty'),
    ).not.toBeInTheDocument()
  })

  it('renders raw description plus the fallback note when plain is missing', () => {
    const finding = makeFinding({
      plain_description: null,
      description: 'Raw scanner blob.',
    })
    renderRow(finding)

    expect(screen.getByTestId('finding-description')).toHaveTextContent(
      'Raw scanner blob.',
    )
    expect(screen.getByTestId('description-fallback-note')).toHaveTextContent(
      /auto-summary unavailable/i,
    )
  })

  it('renders an empty-state line when both description fields are missing', () => {
    const finding = makeFinding({
      plain_description: null,
      description: null,
    })
    renderRow(finding)

    expect(
      screen.queryByTestId('finding-description'),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByTestId('description-fallback-note'),
    ).not.toBeInTheDocument()
    expect(
      screen.getByTestId('finding-description-empty'),
    ).toHaveTextContent(/no description available/i)
  })
})
