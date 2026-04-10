import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import PlannerResultCard from '../PlannerResultCard'
import type { PlanOutput } from '@/api/client'

const baseData: PlanOutput = {
  plan_steps: [
    'Upgrade lodash from 4.17.20 to 4.17.21',
    'Run npm install to update lockfile',
    'Run test suite to verify no regressions',
  ],
  definition_of_done: [
    'lodash >= 4.17.21 in package.json',
    'Tests pass',
    'Snyk re-scan shows finding resolved',
  ],
  interim_mitigation: 'Validate all merge() inputs at API boundary',
  dependencies: ['npm access for package update'],
  estimated_effort: 'Small (single dependency bump)',
  suggested_due_date: '2026-04-15',
  validation_method: 'Re-run Snyk scan after deployment',
}

describe('PlannerResultCard', () => {
  it('renders agent label', () => {
    render(<PlannerResultCard data={baseData} />)
    expect(screen.getByText('Remediation plan')).toBeInTheDocument()
  })

  it('renders numbered fix steps', () => {
    render(<PlannerResultCard data={baseData} />)
    expect(screen.getByText('1.')).toBeInTheDocument()
    expect(screen.getByText('2.')).toBeInTheDocument()
    expect(screen.getByText('3.')).toBeInTheDocument()
    expect(screen.getByText(/Upgrade lodash/)).toBeInTheDocument()
  })

  it('renders interim mitigation', () => {
    render(<PlannerResultCard data={baseData} />)
    expect(screen.getByText(/Validate all merge/)).toBeInTheDocument()
  })

  it('renders effort estimate', () => {
    render(<PlannerResultCard data={baseData} />)
    expect(screen.getByText('Small (single dependency bump)')).toBeInTheDocument()
  })

  it('renders definition of done checklist', () => {
    render(<PlannerResultCard data={baseData} />)
    expect(screen.getByText(/lodash >= 4.17.21/)).toBeInTheDocument()
    expect(screen.getByText('Tests pass')).toBeInTheDocument()
  })

  it('renders confidence badge', () => {
    render(<PlannerResultCard data={baseData} confidence={0.9} />)
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('shows expandable details section', async () => {
    const user = userEvent.setup()
    render(<PlannerResultCard data={baseData} />)

    expect(screen.queryByText('Dependencies')).not.toBeInTheDocument()
    await user.click(screen.getByText('View details'))
    expect(screen.getByText('Dependencies')).toBeInTheDocument()
    expect(screen.getByText('npm access for package update')).toBeInTheDocument()
  })

  it('handles empty plan steps gracefully', () => {
    const emptyData: PlanOutput = {
      plan_steps: [],
      definition_of_done: [],
      interim_mitigation: null,
      dependencies: [],
      estimated_effort: null,
      suggested_due_date: null,
      validation_method: null,
    }
    render(<PlannerResultCard data={emptyData} />)
    expect(screen.getByText('Remediation plan')).toBeInTheDocument()
  })
})
