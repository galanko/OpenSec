import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import ExposureResultCard from '../ExposureResultCard'
import type { ExposureOutput } from '@/api/client'

const baseData: ExposureOutput = {
  recommended_urgency: 'high',
  environment: 'production',
  internet_facing: false,
  reachable: 'Likely reachable',
  reachability_evidence: 'Import chain: src/api/auth.ts -> lodash.merge()',
  business_criticality: 'Medium',
  blast_radius: 'Affects 3 downstream services',
}

describe('ExposureResultCard', () => {
  it('renders agent label', () => {
    render(<ExposureResultCard data={baseData} />)
    expect(screen.getByText('Exposure analysis')).toBeInTheDocument()
  })

  it('renders reachability', () => {
    render(<ExposureResultCard data={baseData} />)
    expect(screen.getByText('Likely reachable')).toBeInTheDocument()
  })

  it('renders environment', () => {
    render(<ExposureResultCard data={baseData} />)
    expect(screen.getByText('production')).toBeInTheDocument()
  })

  it('renders internet-facing as Yes/No', () => {
    render(<ExposureResultCard data={baseData} />)
    expect(screen.getByText('No')).toBeInTheDocument()

    const { unmount } = render(<ExposureResultCard data={{ ...baseData, internet_facing: true }} />)
    expect(screen.getByText('Yes')).toBeInTheDocument()
    unmount()
  })

  it('renders urgency bar with label', () => {
    render(<ExposureResultCard data={baseData} />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('renders confidence badge', () => {
    render(<ExposureResultCard data={baseData} confidence={0.5} />)
    // "Medium" appears both as criticality value and confidence label
    const mediumTexts = screen.getAllByText('Medium')
    expect(mediumTexts.length).toBeGreaterThanOrEqual(2) // criticality + confidence
  })

  it('shows expandable analysis section', async () => {
    const user = userEvent.setup()
    render(<ExposureResultCard data={baseData} />)

    expect(screen.queryByText('Blast radius')).not.toBeInTheDocument()
    await user.click(screen.getByText('View full analysis'))
    expect(screen.getByText('Blast radius')).toBeInTheDocument()
    expect(screen.getByText('Affects 3 downstream services')).toBeInTheDocument()
  })

  it('handles missing optional fields', () => {
    const minimalData: ExposureOutput = {
      recommended_urgency: 'low',
      environment: null,
      internet_facing: null,
      reachable: null,
      reachability_evidence: null,
      business_criticality: null,
      blast_radius: null,
    }
    render(<ExposureResultCard data={minimalData} />)
    expect(screen.getByText('Exposure analysis')).toBeInTheDocument()
    expect(screen.getByText('Low')).toBeInTheDocument()
  })
})
