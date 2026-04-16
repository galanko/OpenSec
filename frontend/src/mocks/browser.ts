/**
 * MSW browser worker — dev-only. Session G removed the mocks for every route
 * that now has a real backend; what's left is the Findings list + detail,
 * which still live behind mocks pending a follow-up backend PR.
 *
 * Dev now expects ``scripts/dev.sh`` (FastAPI on :8000 + Vite on :5173) to be
 * running. Set ``VITE_USE_REAL_API=1`` or ``VITE_MSW=off`` to skip this worker
 * entirely and let every request through to the proxy.
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
