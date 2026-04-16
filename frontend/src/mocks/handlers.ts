/**
 * Dev-time + test-time MSW handlers.
 *
 * Session G removed the mocks for the eight routes that now have real
 * backend implementations (onboarding, dashboard, assessment status,
 * posture-fix, completion share-action). What's left is the Findings list
 * + detail, which still lives behind mocks pending a follow-up backend PR.
 *
 * Test files that need the removed handlers register them per-test from
 * ``src/test/msw/sessionHandlers.ts`` via ``server.use(...)``.
 */

import { http, HttpResponse } from 'msw'
import { sampleFindings } from './fixtures/dashboard'

export const handlers = [
  http.get('/api/findings', () => HttpResponse.json(sampleFindings)),
  http.get('/api/findings/:id', ({ params }) => {
    const finding = sampleFindings.find((f) => f.id === params.id)
    if (!finding) {
      return HttpResponse.json({ detail: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json(finding)
  }),
]

// Re-export session-handler helpers so existing tests that import from
// '@/mocks/handlers' keep working. The helpers themselves now live under
// ``src/test/msw/sessionHandlers.ts``.
export {
  setDashboardFixture,
  getActiveDashboardFixture,
  resetStatusPoll,
  type ShareAction,
} from '../test/msw/sessionHandlers'
