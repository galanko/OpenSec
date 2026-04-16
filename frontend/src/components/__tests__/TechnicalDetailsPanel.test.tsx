import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import TechnicalDetailsPanel from '../TechnicalDetailsPanel'

describe('<TechnicalDetailsPanel />', () => {
  const rawPayload = {
    cve: 'CVE-2024-4067',
    cvss_score: 7.5,
    attack_vector: 'regex denial-of-service',
  }

  it('renders a native <details> element collapsed by default', () => {
    const { container } = render(
      <TechnicalDetailsPanel sourceId="CVE-2024-4067" rawPayload={rawPayload} />,
    )
    const details = container.querySelector('details')
    expect(details).not.toBeNull()
    expect(details?.hasAttribute('open')).toBe(false)
  })

  it('summary uses sentence case "Technical details"', () => {
    render(
      <TechnicalDetailsPanel sourceId="CVE-2024-4067" rawPayload={rawPayload} />,
    )
    expect(screen.getByText('Technical details')).toBeInTheDocument()
  })

  it('renders CVE, CVSS, attack vector when payload is present', () => {
    render(
      <TechnicalDetailsPanel sourceId="CVE-2024-4067" rawPayload={rawPayload} />,
    )
    expect(screen.getByText('CVE-2024-4067')).toBeInTheDocument()
    expect(screen.getByText(/7\.5/)).toBeInTheDocument()
    expect(
      screen.getByText(/regex denial-of-service/i),
    ).toBeInTheDocument()
  })

  it('tolerates a null rawPayload', () => {
    render(
      <TechnicalDetailsPanel sourceId="CVE-2024-4067" rawPayload={null} />,
    )
    expect(screen.getByText('CVE-2024-4067')).toBeInTheDocument()
  })
})
