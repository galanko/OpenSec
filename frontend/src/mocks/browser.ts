/**
 * MSW browser worker — used only in dev when backend Session B is not yet live.
 * Start from `main.tsx` behind an env flag to keep production untouched.
 */

import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers)
