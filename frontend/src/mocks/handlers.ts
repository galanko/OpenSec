/**
 * Dev-time + test-time MSW handlers for routes that don't yet have a real
 * backend (Findings list + detail). Tests that need additional handlers
 * register them per-test via ``server.use(...)`` from ``src/test/msw``.
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

export {
  setDashboardFixture,
  getActiveDashboardFixture,
  resetStatusPoll,
  type ShareAction,
} from '../test/msw/sessionHandlers'
