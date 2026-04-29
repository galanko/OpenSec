import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router'
import SideNav from '../SideNav'

function renderSideNav(initialPath = '/issues') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <SideNav />
    </MemoryRouter>,
  )
}

describe('SideNav (PRD-0006 Phase 1)', () => {
  it('renders exactly two primary nav links + the Settings footer link', () => {
    renderSideNav()
    const nav = screen.getByRole('navigation', { name: /Primary/i })
    const links = nav.querySelectorAll('a')
    expect(links).toHaveLength(2)

    expect(screen.getByLabelText('Dashboard')).toBeInTheDocument()
    expect(screen.getByLabelText('Issues')).toBeInTheDocument()
    expect(screen.getByLabelText('Settings')).toBeInTheDocument()
  })

  it('does not render Findings, Workspace, or History entries', () => {
    renderSideNav()
    expect(screen.queryByLabelText('Findings')).toBeNull()
    expect(screen.queryByLabelText('Workspace')).toBeNull()
    expect(screen.queryByLabelText('History')).toBeNull()
  })

  it('routes the Issues link to /issues with the inbox icon', () => {
    renderSideNav()
    const issues = screen.getByLabelText('Issues')
    expect(issues.getAttribute('href')).toBe('/issues')
    expect(issues.querySelector('.material-symbols-outlined')?.textContent).toBe(
      'inbox',
    )
  })

  it('marks the Issues link active when the route is /issues', () => {
    renderSideNav('/issues')
    const issues = screen.getByLabelText('Issues')
    // Active class is "text-primary" + bg pill (tonal). The NavLink renders
    // aria-current="page" when active.
    expect(issues.getAttribute('aria-current')).toBe('page')
  })

  it('marks the Dashboard link active when the route is /dashboard', () => {
    renderSideNav('/dashboard')
    expect(screen.getByLabelText('Dashboard').getAttribute('aria-current')).toBe(
      'page',
    )
    expect(screen.getByLabelText('Issues').getAttribute('aria-current')).not.toBe(
      'page',
    )
  })

  it('Settings is anchored to the bottom via mt-auto', () => {
    renderSideNav()
    const settings = screen.getByLabelText('Settings')
    expect(settings.className).toMatch(/mt-auto/)
  })
})
