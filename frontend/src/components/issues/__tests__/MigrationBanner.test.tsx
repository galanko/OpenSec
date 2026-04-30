import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { MigrationBanner } from '../MigrationBanner'

const STORAGE_KEY = 'opensec.issues.migrationBannerDismissed'

describe('MigrationBanner', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })
  afterEach(() => {
    sessionStorage.clear()
  })

  it('renders the announcement copy and "what\'s coming" link', () => {
    render(<MigrationBanner />)
    expect(
      screen.getByText(/Review section pinned to the top/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /what's coming/i })).toBeInTheDocument()
  })

  it('renders an accessible dismiss button', () => {
    render(<MigrationBanner />)
    expect(screen.getByRole('button', { name: /dismiss/i })).toBeInTheDocument()
  })

  it('hides itself after dismiss is clicked', () => {
    render(<MigrationBanner />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(screen.queryByText(/Review section pinned/i)).toBeNull()
  })

  it('persists dismissal in sessionStorage', () => {
    render(<MigrationBanner />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe('1')
  })

  it('does not render when sessionStorage flag is set', () => {
    sessionStorage.setItem(STORAGE_KEY, '1')
    render(<MigrationBanner />)
    expect(screen.queryByText(/Review section pinned/i)).toBeNull()
  })

  it('the see-what\'s-coming link points to a github.com URL', () => {
    render(<MigrationBanner />)
    const link = screen.getByRole('link', { name: /what's coming/i })
    expect(link.getAttribute('href') ?? '').toMatch(/github\.com/i)
  })
})
