import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CompletionStatusCard from '../completion/CompletionStatusCard'

describe('CompletionStatusCard (placeholder)', () => {
  it('renders all declared props', () => {
    render(
      <CompletionStatusCard
        completionId="c-123"
        completedAt="2026-04-15T12:00:00Z"
        onReopenSummary={() => {}}
      />,
    )
    expect(screen.getByTestId('CompletionStatusCard')).toBeInTheDocument()
    expect(screen.getByText('c-123')).toBeInTheDocument()
    expect(screen.getByText('2026-04-15T12:00:00Z')).toBeInTheDocument()
    expect(screen.getByText('function')).toBeInTheDocument()
  })
})
