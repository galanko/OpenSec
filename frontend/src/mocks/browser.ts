/**
 * MSW browser worker — dev-only. Handles the routes in ``./handlers`` that
 * don't yet have a real backend. Everything else flows through the Vite proxy
 * to FastAPI. Set ``VITE_USE_REAL_API=1`` or ``VITE_MSW=off`` to bypass.
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
