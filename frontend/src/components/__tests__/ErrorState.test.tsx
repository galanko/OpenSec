import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ErrorState from '../ErrorState'

describe('ErrorState', () => {
  it('renders title and subtitle', () => {
    render(<ErrorState title="Something went wrong" subtitle="Please try again later." />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('Please try again later.')).toBeInTheDocument()
  })

  it('renders error icon', () => {
    render(<ErrorState title="Error" />)
    expect(screen.getByText('error_outline')).toBeInTheDocument()
  })

  it('renders retry button when onRetry provided', () => {
    const onRetry = vi.fn()
    render(<ErrorState title="Error" onRetry={onRetry} />)
    expect(screen.getByText('Try again')).toBeInTheDocument()
  })

  it('calls onRetry when button clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<ErrorState title="Error" onRetry={onRetry} />)
    await user.click(screen.getByText('Try again'))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('hides retry button when onRetry not provided', () => {
    render(<ErrorState title="Error" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('uses custom retry label', () => {
    render(<ErrorState title="Error" onRetry={() => {}} retryLabel="Reload page" />)
    expect(screen.getByText('Reload page')).toBeInTheDocument()
  })
})
