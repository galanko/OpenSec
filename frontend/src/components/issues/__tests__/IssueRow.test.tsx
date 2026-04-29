import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Finding, IssueStage } from '../../../api/client'
import { IssueRow } from '../IssueRow'

function makeFinding(overrides: Partial<Finding> & { stage: IssueStage }): Finding {
  return {
    id: 'f-1',
    source_type: 'trivy',
    source_id: 'CVE-2024-1234',
    title: 'CVE-2024-1234 in libfoo',
    description: 'Remote code execution',
    raw_severity: 'critical',
    normalized_priority: 'P1',
    asset_id: 'srv-web-01',
    asset_label: 'Web Server 01',
    status: 'new',
    likely_owner: null,
    why_this_matters: null,
    raw_payload: null,
    plain_description: null,
    created_at: '2026-04-29T12:00:00Z',
    updated_at: '2026-04-29T12:00:00Z',
    type: 'dependency',
    derived: {
      section:
        overrides.stage === 'plan_ready' ||
        overrides.stage === 'pr_ready' ||
        overrides.stage === 'pr_awaiting_val'
          ? 'review'
          : overrides.stage === 'todo'
            ? 'todo'
            : overrides.stage === 'fixed' ||
                overrides.stage === 'wont_fix' ||
                overrides.stage === 'accepted' ||
                overrides.stage === 'false_positive' ||
                overrides.stage === 'deferred'
              ? 'done'
              : 'in_progress',
      stage: overrides.stage,
      workspace_id: 'w-1',
      pr_url: null,
    },
    ...overrides,
  }
}

describe('IssueRow', () => {
  it('renders title and source-id metadata row', () => {
    render(<IssueRow finding={makeFinding({ stage: 'todo' })} />)
    expect(screen.getByText(/CVE-2024-1234 in libfoo/)).toBeInTheDocument()
    // The source_id appears in the metadata row in mono.
    const ids = screen.getAllByText('CVE-2024-1234')
    expect(ids.length).toBeGreaterThan(0)
  })

  it('renders the bug_report icon for vulnerability type', () => {
    render(<IssueRow finding={makeFinding({ stage: 'todo' })} />)
    const row = screen.getByRole('row')
    const icons = Array.from(row.querySelectorAll('.material-symbols-outlined')).map(
      (el) => el.textContent,
    )
    expect(icons).toContain('bug_report')
  })

  it('renders Review plan action for plan_ready stage', () => {
    render(<IssueRow finding={makeFinding({ stage: 'plan_ready' })} />)
    expect(screen.getByRole('button', { name: /review plan/i })).toBeInTheDocument()
  })

  it('renders Review PR action for pr_ready stage', () => {
    render(<IssueRow finding={makeFinding({ stage: 'pr_ready' })} />)
    expect(screen.getByRole('button', { name: /review pr/i })).toBeInTheDocument()
  })

  it('renders Review PR action for pr_awaiting_val stage', () => {
    render(<IssueRow finding={makeFinding({ stage: 'pr_awaiting_val' })} />)
    expect(screen.getByRole('button', { name: /review pr/i })).toBeInTheDocument()
  })

  it('renders Start action for todo stage', () => {
    render(<IssueRow finding={makeFinding({ stage: 'todo' })} />)
    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument()
  })

  it('renders chevron-only action (no button) for in-flight stages', () => {
    render(<IssueRow finding={makeFinding({ stage: 'generating' })} />)
    // Should not have a "Start" / "Review plan" / "Review PR" button.
    expect(screen.queryByRole('button', { name: /start|review/i })).toBeNull()
    // The chevron-right Material symbol must be present for the view-only
    // action slot.
    const row = screen.getByRole('row')
    const symbols = Array.from(row.querySelectorAll('.material-symbols-outlined')).map(
      (el) => el.textContent,
    )
    expect(symbols).toContain('chevron_right')
  })

  it('renders chevron-only action for done stages and sets dim opacity', () => {
    render(<IssueRow finding={makeFinding({ stage: 'fixed' })} dim />)
    expect(screen.queryByRole('button', { name: /start|review/i })).toBeNull()
    const row = screen.getByRole('row')
    expect(row.className).toMatch(/opacity/)
  })

  it('fires onActivate when the row is clicked', () => {
    const onActivate = vi.fn()
    render(
      <IssueRow finding={makeFinding({ stage: 'todo' })} onActivate={onActivate} />,
    )
    fireEvent.click(screen.getByRole('row'))
    expect(onActivate).toHaveBeenCalledTimes(1)
  })

  it('fires onActivate when the action button is clicked', () => {
    const onActivate = vi.fn()
    render(
      <IssueRow
        finding={makeFinding({ stage: 'plan_ready' })}
        onActivate={onActivate}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /review plan/i }))
    expect(onActivate).toHaveBeenCalledTimes(1)
  })

  it('applies the focus-visible ring style when focused prop is set', () => {
    render(<IssueRow finding={makeFinding({ stage: 'todo' })} focused />)
    const row = screen.getByRole('row')
    expect(row.style.boxShadow).toContain('inset')
  })

  it('renders the severity hairline + badge + stage chip in the row', () => {
    render(<IssueRow finding={makeFinding({ stage: 'plan_ready' })} />)
    const row = screen.getByRole('row')
    // Stage chip uses our atom; severity badge uses our atom too.
    expect(row.querySelector('[data-testid="stage-chip-plan_ready"]')).not.toBeNull()
    expect(row.querySelector('[aria-label*="Severity"]')).not.toBeNull()
  })
})
