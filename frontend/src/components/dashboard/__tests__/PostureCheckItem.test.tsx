import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import PostureCheckItem from '../PostureCheckItem'

describe('<PostureCheckItem />', () => {
  it('renders a compact passing state with a checkmark icon', () => {
    render(
      <PostureCheckItem
        checkName="branch_protection"
        status="pass"
        label="Main branch is protected"
      />,
    )
    const item = screen.getByTestId('posture-check-item')
    expect(item.dataset.state).toBe('pass')
    expect(
      screen.getByText('Main branch is protected'),
    ).toBeInTheDocument()
    expect(item.querySelector('.material-symbols-outlined')).toHaveTextContent(
      'check_circle',
    )
  })

  it('renders an advisory row in muted tone', () => {
    render(
      <PostureCheckItem
        checkName="license_file"
        status="advisory"
        label="LICENSE is present but outdated"
      />,
    )
    const item = screen.getByTestId('posture-check-item')
    expect(item.dataset.state).toBe('advisory')
  })

  it('renders a failing security_md row with "Generate and open PR" CTA', async () => {
    const onGenerate = vi.fn()
    render(
      <PostureCheckItem
        checkName="security_md"
        status="fail"
        label="SECURITY.md is missing"
        description="We can generate a starter file in a PR."
        onGenerate={onGenerate}
      />,
    )
    const button = screen.getByRole('button', {
      name: /generate and open pr/i,
    })
    expect(button).toBeInTheDocument()
    await userEvent.click(button)
    expect(onGenerate).toHaveBeenCalledWith('security_md')
  })

  it('hides the CTA for non-generator failing checks', () => {
    render(
      <PostureCheckItem
        checkName="branch_protection"
        status="fail"
        label="Main branch is not protected"
      />,
    )
    expect(
      screen.queryByRole('button', { name: /generate and open pr/i }),
    ).not.toBeInTheDocument()
  })
})
