/**
 * MSW handlers for the dashboard, findings, posture, and completion APIs.
 *
 * Tests override the default fixture with `setDashboardFixture(name)` or
 * `server.use(...)` for fine-grained control. Session G removes the handlers
 * for routes that get real backend implementations and keeps everything else.
 *
 * The share-action endpoint returns HTTP 200 with a JSON body to mirror the
 * frozen Session 0 contract (see backend/opensec/api/routes/completion.py).
 * Frontend callers treat the response as fire-and-forget; we ignore the body.
 */

import { http, HttpResponse } from 'msw'
import {
  assessmentStatusSteps,
  getDashboardFixture,
  sampleFindings,
  type DashboardFixtureName,
} from './fixtures/dashboard'

let activeFixture: DashboardFixtureName = 'grade-C-with-issues'

export function setDashboardFixture(name: DashboardFixtureName): void {
  activeFixture = name
}

export function getActiveDashboardFixture(): DashboardFixtureName {
  return activeFixture
}

let statusPollIndex = 0

export function resetStatusPoll(): void {
  statusPollIndex = 0
}

export type ShareAction = 'download' | 'copy_text' | 'copy_markdown'

export const handlers = [
  // Dashboard aggregate payload
  http.get('/api/dashboard', () =>
    HttpResponse.json(getDashboardFixture(activeFixture)),
  ),

  // Assessment status — advances through fixture steps on each call
  http.get('/api/assessment/status/:id', () => {
    const step = assessmentStatusSteps[
      Math.min(statusPollIndex, assessmentStatusSteps.length - 1)
    ]
    statusPollIndex += 1
    return HttpResponse.json(step)
  }),

  // Posture-check fix — returns the same shape the contract promises
  http.post('/api/posture/fix/:checkName', ({ params }) => {
    const checkName = params.checkName as 'security_md' | 'dependabot_config'
    return HttpResponse.json({
      check_name: checkName,
      workspace_id: `ws_${checkName}_stub`,
    })
  }),

  // Findings list (used by FindingsPage + detail)
  http.get('/api/findings', () => HttpResponse.json(sampleFindings)),
  http.get('/api/findings/:id', ({ params }) => {
    const finding = sampleFindings.find((f) => f.id === params.id)
    if (!finding) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(finding)
  }),

  // Completion share-action — Session F
  http.post('/api/completion/:id/share-action', async ({ params, request }) => {
    const body = (await request.json()) as { action: ShareAction }
    return HttpResponse.json(
      {
        completion_id: String(params.id),
        share_actions_used: [body.action],
      },
      { status: 200 },
    )
  }),
]
