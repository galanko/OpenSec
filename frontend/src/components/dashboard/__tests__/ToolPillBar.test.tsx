import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import ToolPillBar from '@/components/dashboard/ToolPillBar'
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
    label: 'Semgrep',
    version: null,
    icon: 'code',
    state: 'active',
    result: null,
  },
  {
    id: 'posture',
    label: '15 posture checks',
    version: null,
    icon: 'rule',
    state: 'pending',
    result: null,
  },
]

describe('ToolPillBar', () => {
  it('renders all three pills with correct data-state', () => {
    render(<ToolPillBar tools={tools} />)
    expect(screen.getByTestId('tool-pill-trivy')).toHaveAttribute(
      'data-state',
      'done',
    )
    expect(screen.getByTestId('tool-pill-semgrep')).toHaveAttribute(
      'data-state',
      'active',
    )
    expect(screen.getByTestId('tool-pill-posture')).toHaveAttribute(
      'data-state',
      'pending',
    )
  })

  it('done pill renders the result text tail; pending does not', () => {
    render(<ToolPillBar tools={tools} />)
    const done = screen.getByTestId('tool-pill-trivy')
    expect(done).toHaveTextContent(/7 findings/)
    const pending = screen.getByTestId('tool-pill-posture')
    expect(pending).not.toHaveTextContent('findings')
    expect(pending).not.toHaveTextContent('pass')
  })

  it('active pill uses animate-pulse-subtle utility class', () => {
    render(<ToolPillBar tools={tools} />)
    const active = screen.getByTestId('tool-pill-semgrep')
    expect(active.className).toContain('animate-pulse-subtle')
  })

  it('skipped pill is visually distinct and has no result tail', () => {
    const skipped: AssessmentTool[] = [
      {
        id: 'semgrep',
        label: 'Semgrep',
        version: null,
        icon: 'code',
        state: 'skipped',
        result: null,
      },
    ]
    render(<ToolPillBar tools={skipped} />)
    const pill = screen.getByTestId('tool-pill-semgrep')
    expect(pill).toHaveAttribute('data-state', 'skipped')
    expect(pill.className).toContain('line-through')
    expect(pill).not.toHaveTextContent('findings')
  })

  it('size sm tightens padding + font size', () => {
    const { container } = render(<ToolPillBar tools={tools} size="sm" />)
    const pill = container.querySelector('[data-testid="tool-pill-trivy"]')
    expect(pill).not.toBeNull()
    expect(pill!.className).toContain('px-2.5')
    expect(pill!.className).toContain('text-[11px]')
  })
})
