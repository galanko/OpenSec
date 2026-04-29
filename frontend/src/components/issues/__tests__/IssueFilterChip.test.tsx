import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { IssueFilterChip } from '../IssueFilterChip'

describe('IssueFilterChip', () => {
  it('renders the children label', () => {
    render(<IssueFilterChip>Critical</IssueFilterChip>)
    expect(screen.getByRole('button', { name: /critical/i })).toBeInTheDocument()
  })

  it('marks active state with on-surface bg + surface-container-lowest text', () => {
    render(<IssueFilterChip active>Critical</IssueFilterChip>)
    const btn = screen.getByRole('button')
    expect(btn.className).toMatch(/bg-on-surface/)
    expect(btn.className).toMatch(/text-surface-container-lowest/)
  })

  it('renders the inactive ghost border via outline-variant', () => {
    render(<IssueFilterChip>Critical</IssueFilterChip>)
    const btn = screen.getByRole('button')
    expect(btn.className).toMatch(/border-outline-variant/)
  })

  it('renders the leading icon when provided', () => {
    render(<IssueFilterChip icon="warning">High</IssueFilterChip>)
    const icon = screen.getByRole('button').querySelector('.material-symbols-outlined')
    expect(icon?.textContent).toBe('warning')
  })

  it('renders the trailing count badge when count is provided', () => {
    render(<IssueFilterChip count={7}>Critical</IssueFilterChip>)
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('does NOT render the count badge when count is undefined', () => {
    render(<IssueFilterChip>Critical</IssueFilterChip>)
    expect(screen.queryByText(/^\d+$/)).toBeNull()
  })

  it('renders the count even when the count is zero', () => {
    render(<IssueFilterChip count={0}>Critical</IssueFilterChip>)
    expect(screen.getByText('0')).toBeInTheDocument()
  })

  it('fires onClick when clicked', () => {
    const onClick = vi.fn()
    render(<IssueFilterChip onClick={onClick}>Critical</IssueFilterChip>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('exposes aria-pressed reflecting the active state', () => {
    render(<IssueFilterChip active>Critical</IssueFilterChip>)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
  })

  it('exposes aria-pressed=false when inactive', () => {
    render(<IssueFilterChip>Critical</IssueFilterChip>)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('false')
  })
})
