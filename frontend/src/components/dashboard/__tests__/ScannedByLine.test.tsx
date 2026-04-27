import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ScannedByLine from '@/components/dashboard/ScannedByLine'
import type { components } from '@/api/types'

type AssessmentTool = components['schemas']['AssessmentTool']

const tools: AssessmentTool[] = [
  {
    id: 'trivy',
    label: 'Trivy 0.52',
    version: '0.52.0',
    icon: 'bug_report',
    state: 'done',
    result: { kind: 'findings_count', value: 7, text: '7 findings' },
  },
  {
    id: 'semgrep',
    label: 'Semgrep 1.70',
    version: '1.70.0',
    icon: 'code',
    state: 'done',
    result: { kind: 'findings_count', value: 3, text: '3 findings' },
  },
  {
    id: 'posture',
    label: '15 posture checks',
    version: null,
    icon: 'rule',
    state: 'done',
    result: { kind: 'pass_count', value: 12, text: '12 pass' },
  },
]

describe('ScannedByLine', () => {
  it('renders Scanned by eyebrow with three result-bearing pills', () => {
    render(<ScannedByLine tools={tools} />)
    const line = screen.getByTestId('scanned-by-line')
    expect(line.textContent).toContain('Scanned by')
    expect(screen.getByTestId('tool-pill-trivy').textContent).toContain(
      '7 findings',
    )
    expect(screen.getByTestId('tool-pill-semgrep').textContent).toContain(
      '3 findings',
    )
    expect(screen.getByTestId('tool-pill-posture').textContent).toContain(
      '12 pass',
    )
  })
})
