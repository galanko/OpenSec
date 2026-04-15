import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CompletionProgressCard from '../completion/CompletionProgressCard'

describe('CompletionProgressCard (placeholder)', () => {
  it('renders all declared props', () => {
    render(
      <CompletionProgressCard
        criteriaMet={3}
        criteriaTotal={5}
        grade="B"
        repoName="acme/api"
      />,
    )
    expect(screen.getByTestId('CompletionProgressCard')).toBeInTheDocument()
    expect(screen.getByText('acme/api')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })
})
