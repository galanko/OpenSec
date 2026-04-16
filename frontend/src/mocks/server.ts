/**
 * MSW server for vitest + Node environment.
 * Browser counterpart lives in `browser.ts` (started from main.tsx in dev only).
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
