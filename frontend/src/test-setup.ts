import '@testing-library/jest-dom/vitest'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './mocks/server'
import { resetStatusPoll, setDashboardFixture } from './mocks/handlers'

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

// Reset between tests so fixture choice and handler overrides don't leak.
afterEach(() => {
  server.resetHandlers()
  setDashboardFixture('grade-C-with-issues')
  resetStatusPoll()
})

afterAll(() => server.close())
