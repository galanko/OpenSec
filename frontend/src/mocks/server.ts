/**
 * MSW server for vitest + Node environment. Loads only the findings handlers
 * that remain in the global set; component tests install the session-specific
 * handlers (onboarding, dashboard, posture-fix, completion share-action) via
 * ``sessionHandlers`` + ``server.use(...)`` in ``src/test-setup.ts``.
 */

import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
