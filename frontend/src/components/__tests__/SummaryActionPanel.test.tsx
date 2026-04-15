import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import SummaryActionPanel from '../completion/SummaryActionPanel'

describe('SummaryActionPanel (placeholder)', () => {
  it('renders all declared props', () => {
    render(
      <SummaryActionPanel
        completionId="c-123"
        summaryText="Secure!"
        summaryMarkdown="**Secure!**"
        filename="opensec-summary.png"
      />,
    )
    expect(screen.getByTestId('SummaryActionPanel')).toBeInTheDocument()
    expect(screen.getByText('c-123')).toBeInTheDocument()
    expect(screen.getByText('opensec-summary.png')).toBeInTheDocument()
    expect(screen.getByText('Secure!')).toBeInTheDocument()
    expect(screen.getByText('**Secure!**')).toBeInTheDocument()
  })
})
