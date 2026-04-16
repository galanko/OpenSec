import { describe, expect, it } from 'vitest'
import {
  assessmentRunningPayload,
  gradeACompletionHoldingPayload,
  gradeCWithIssuesPayload,
} from '../fixtures/dashboard'
import { setDashboardFixture } from '../handlers'

const BASE = 'http://localhost:5173'

describe('MSW dashboard handlers', () => {
  it('returns the grade-C fixture by default', async () => {
    const resp = await fetch(`${BASE}/api/dashboard`)
    expect(resp.status).toBe(200)
    const body = await resp.json()
    expect(body).toEqual(gradeCWithIssuesPayload)
  })

  it('honours setDashboardFixture("assessment-running")', async () => {
    setDashboardFixture('assessment-running')
    const body = await (await fetch(`${BASE}/api/dashboard`)).json()
    expect(body).toEqual(assessmentRunningPayload)
  })

  it('honours setDashboardFixture("grade-A-completion-holding")', async () => {
    setDashboardFixture('grade-A-completion-holding')
    const body = await (await fetch(`${BASE}/api/dashboard`)).json()
    expect(body).toEqual(gradeACompletionHoldingPayload)
  })

  it('walks the assessment status steps on successive polls', async () => {
    const first = await (
      await fetch(`${BASE}/api/assessment/status/asmt_running_001`)
    ).json()
    const second = await (
      await fetch(`${BASE}/api/assessment/status/asmt_running_001`)
    ).json()
    expect(first.progress_pct).toBe(10)
    expect(second.progress_pct).toBe(30)
  })

  it('accepts posture fix POST and returns a stub workspace id', async () => {
    const resp = await fetch(`${BASE}/api/posture/fix/security_md`, {
      method: 'POST',
    })
    expect(resp.status).toBe(200)
    const body = await resp.json()
    expect(body.check_name).toBe('security_md')
    expect(body.workspace_id).toMatch(/^ws_/)
  })
})
