import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import CompletionProgressCard from '../CompletionProgressCard'

describe('<CompletionProgressCard />', () => {
  it('renders the "3 of 5 met" state with the correct copy', () => {
    render(
      <CompletionProgressCard
        criteriaMet={3}
        criteriaTotal={5}
        grade="C"
        repoName="acme/fast-markdown"
      />,
    )
    expect(screen.getByText('Completion progress')).toBeInTheDocument()
    expect(
      screen.getByText(/3 criteria met · 2 remaining/i),
    ).toBeInTheDocument()
  })

  it('renders five pills — met pills get data-state="met", remaining get "empty"', () => {
    render(
      <CompletionProgressCard
        criteriaMet={3}
        criteriaTotal={5}
        grade="C"
        repoName="acme/fast-markdown"
      />,
    )
    const pills = screen.getAllByTestId('criteria-pill')
    expect(pills).toHaveLength(5)
    expect(pills.filter((p) => p.dataset.state === 'met')).toHaveLength(3)
    expect(pills.filter((p) => p.dataset.state === 'empty')).toHaveLength(2)
  })

  it('uses "completion" vocabulary, never "badge"', () => {
    const { container } = render(
      <CompletionProgressCard
        criteriaMet={3}
        criteriaTotal={5}
        grade="C"
        repoName="acme/fast-markdown"
      />,
    )
    expect(container.textContent?.toLowerCase()).not.toMatch(/badge/)
  })

  it('handles the "all met" state with singular "remaining" phrasing hidden', () => {
    render(
      <CompletionProgressCard
        criteriaMet={5}
        criteriaTotal={5}
        grade="A"
        repoName="acme/fast-markdown"
      />,
    )
    expect(
      screen.getByText(/5 criteria met · all complete/i),
    ).toBeInTheDocument()
  })
})
