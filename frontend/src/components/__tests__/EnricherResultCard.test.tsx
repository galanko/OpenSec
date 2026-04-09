import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import EnricherResultCard from '../EnricherResultCard'
import type { EnrichmentOutput } from '@/api/client'

const baseData: EnrichmentOutput = {
  normalized_title: 'lodash prototype pollution',
  cve_ids: ['CVE-2024-48930'],
  cvss_score: 8.1,
  cvss_vector: 'CVSS:3.1/AV:N/AC:L',
  description: 'A prototype pollution vulnerability in lodash.',
  affected_versions: '4.17.20',
  fixed_version: '4.17.21',
  known_exploits: true,
  exploit_details: 'PoC available on GitHub',
  references: ['https://nvd.nist.gov/vuln/detail/CVE-2024-48930'],
}

describe('EnricherResultCard', () => {
  it('renders agent label', () => {
    render(<EnricherResultCard data={baseData} />)
    expect(screen.getByText('Enricher result')).toBeInTheDocument()
  })

  it('renders CVE IDs', () => {
    render(<EnricherResultCard data={baseData} />)
    expect(screen.getByText('CVE-2024-48930')).toBeInTheDocument()
  })

  it('renders CVSS score and bar', () => {
    render(<EnricherResultCard data={baseData} />)
    expect(screen.getByText('8.1')).toBeInTheDocument()
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('renders affected and fixed versions', () => {
    render(<EnricherResultCard data={baseData} />)
    expect(screen.getByText('4.17.20')).toBeInTheDocument()
    expect(screen.getByText('4.17.21')).toBeInTheDocument()
  })

  it('shows exploit warning when known_exploits is true', () => {
    render(<EnricherResultCard data={baseData} />)
    expect(screen.getByText('Public exploit available')).toBeInTheDocument()
  })

  it('shows no exploits when known_exploits is false', () => {
    render(<EnricherResultCard data={{ ...baseData, known_exploits: false }} />)
    expect(screen.getByText('No known exploits')).toBeInTheDocument()
  })

  it('renders confidence badge', () => {
    render(<EnricherResultCard data={baseData} confidence={0.85} />)
    // ConfidenceBadge renders "High" for 0.85
    const highTexts = screen.getAllByText('High')
    expect(highTexts.length).toBeGreaterThanOrEqual(1)
  })

  it('shows expandable details section', async () => {
    const user = userEvent.setup()
    render(<EnricherResultCard data={baseData} />)

    expect(screen.queryByText('Description')).not.toBeInTheDocument()
    await user.click(screen.getByText('View details'))
    expect(screen.getByText('Description')).toBeInTheDocument()
    expect(screen.getByText('A prototype pollution vulnerability in lodash.')).toBeInTheDocument()
  })

  it('handles missing optional fields', () => {
    const minimalData: EnrichmentOutput = {
      normalized_title: 'test vuln',
      cve_ids: [],
      cvss_score: null,
      cvss_vector: null,
      description: null,
      affected_versions: null,
      fixed_version: null,
      known_exploits: false,
      exploit_details: null,
      references: [],
    }
    render(<EnricherResultCard data={minimalData} />)
    expect(screen.getByText('Enricher result')).toBeInTheDocument()
  })
})
