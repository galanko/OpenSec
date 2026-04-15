import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import ShareableSummaryCard from '../completion/ShareableSummaryCard'

describe('ShareableSummaryCard (placeholder)', () => {
  it('renders all six declared props', () => {
    render(
      <ShareableSummaryCard
        repoName="acme/api"
        completedAt="2026-04-15"
        vulnsFixed={12}
        postureChecksPassing={5}
        prsMerged={3}
        grade="A"
      />,
    )
    expect(screen.getByTestId('ShareableSummaryCard')).toBeInTheDocument()
    expect(screen.getByText('acme/api')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('A')).toBeInTheDocument()
  })
})
