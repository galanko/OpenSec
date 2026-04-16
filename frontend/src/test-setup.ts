import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { server } from './mocks/server'
import { resetStatusPoll, setDashboardFixture } from './mocks/handlers'
import { sessionHandlers } from './test/msw/sessionHandlers'

// jsdom ships its own XHR-based fetch that bypasses MSW's Node interceptor.
// Swap in undici's fetch so MSW can intercept both raw test fetches and
// React-Query's `api.*` calls.
import { fetch as undiciFetch } from 'undici'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
;(globalThis as any).fetch = undiciFetch

// Start MSW once for the whole test run.
// `onUnhandledRequest: 'error'` surfaces missing mocks immediately instead of
// creating flaky tests. If a test needs a different handler it can call
// `server.use(...)`; we reset between tests so overrides don't leak.
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))

// Session G moved the Session-B/D/E/F handlers out of the dev-time mock set
// (they now have real backend implementations). Component tests still want
// deterministic responses for those routes, so we register them in every
// test's beforeEach — they're scoped to vitest and never loaded by the dev
// browser worker.
beforeEach(() => {
  server.use(...sessionHandlers)
})

// Reset between tests so fixture choice and handler overrides don't leak.
afterEach(() => {
  server.resetHandlers()
  setDashboardFixture('grade-C-with-issues')
  resetStatusPoll()
})

afterAll(() => server.close())
