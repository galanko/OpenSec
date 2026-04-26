import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import AssessmentSummary from '@/components/dashboard/AssessmentSummary'

const stats = {
  vulnerabilitiesTotal: 7,
  postureFailing: 2,
  posturePassing: 11,
  postureTotal: 13,
  quickWins: 3,
}

describe('AssessmentSummary', () => {
  it('renders three summary cards + grade preview + CTA', () => {
    render(
      <AssessmentSummary
        grade="B"
        criteriaMet={8}
        criteriaTotal={10}
        stats={stats}
        onViewReportCard={() => {}}
      />,
    )
    expect(screen.getByText(/Vulnerabilities/)).toBeInTheDocument()
    expect(screen.getByText(/Posture/)).toBeInTheDocument()
    expect(screen.getByText(/Quick wins/)).toBeInTheDocument()
    expect(
      screen.getByTestId('assessment-summary-grade-preview'),
    ).toBeInTheDocument()
    expect(screen.getByText(/8 of 10 criteria met/)).toBeInTheDocument()
    expect(screen.getByTestId('assessment-summary-cta')).toBeInTheDocument()
  })

  it('CTA fires the onViewReportCard handler', () => {
    const onView = vi.fn()
    render(
      <AssessmentSummary
        grade="B"
        criteriaMet={8}
        criteriaTotal={10}
        stats={stats}
        onViewReportCard={onView}
      />,
    )
    fireEvent.click(screen.getByTestId('assessment-summary-cta'))
    expect(onView).toHaveBeenCalledTimes(1)
  })

  it('CTA disabled while pending', () => {
    render(
      <AssessmentSummary
        grade="B"
        criteriaMet={8}
        criteriaTotal={10}
        stats={stats}
        onViewReportCard={() => {}}
        pending
      />,
    )
    const cta = screen.getByTestId(
      'assessment-summary-cta',
    ) as HTMLButtonElement
    expect(cta.disabled).toBe(true)
  })
})
