import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import PostureRow from '@/components/dashboard/PostureRow'

describe('PostureRow', () => {
  it('pass state renders check_circle in tertiary', () => {
    render(
      <ul>
        <PostureRow
          name="branch_protection"
          displayName="Branch protection enabled"
          state="pass"
          gradeImpact="counts"
        />
      </ul>,
    )
    const row = screen.getByTestId('posture-row')
    expect(row).toHaveAttribute('data-state', 'pass')
    expect(row.textContent).toContain('Branch protection enabled')
  })

  it('fail state uses card-style row with cancel icon', () => {
    render(
      <ul>
        <PostureRow
          name="security_md"
          displayName="SECURITY.md present"
          state="fail"
          gradeImpact="counts"
        />
      </ul>,
    )
    const row = screen.getByTestId('posture-row')
    expect(row).toHaveAttribute('data-state', 'fail')
    expect(row.className).toContain('bg-primary-container/30')
  })

  it('done state renders Draft PR link to pr_url', () => {
    render(
      <ul>
        <PostureRow
          name="actions_pinned_to_sha"
          displayName="Actions pinned to SHA"
          state="done"
          gradeImpact="counts"
          prUrl="https://github.com/a/b/pull/14"
        />
      </ul>,
    )
    const link = screen.getByTestId('posture-row-pr-link')
    expect(link).toHaveAttribute('href', 'https://github.com/a/b/pull/14')
    expect(link).toHaveTextContent(/Draft PR/i)
  })

  it('advisory state renders the advisory chip', () => {
    render(
      <ul>
        <PostureRow
          name="signed_commits"
          displayName="Signed commits"
          state="advisory"
          gradeImpact="advisory"
        />
      </ul>,
    )
    expect(screen.getByTestId('posture-row-advisory-chip')).toBeInTheDocument()
  })

  it('fail state renders the generator slot when provided', () => {
    render(
      <ul>
        <PostureRow
          name="security_md"
          displayName="SECURITY.md present"
          state="fail"
          gradeImpact="counts"
          generatorSlot={<button>Open PR</button>}
        />
      </ul>,
    )
    expect(screen.getByRole('button', { name: /open pr/i })).toBeInTheDocument()
  })
})
