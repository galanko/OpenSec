/**
 * MSW browser worker — used only in dev when the real Session B backend isn't
 * being targeted. Registers every Session's handler slice so the wizard,
 * dashboard, and findings pages all work from `npm run dev` without a backend.
 *
 * Start from `main.tsx` behind an env flag to keep production untouched.
 */

import { setupWorker } from 'msw/browser'
import { onboardingHandlers } from '@/test/msw/onboardingHandlers'
import { handlers } from './handlers'

export const worker = setupWorker(...handlers, ...onboardingHandlers)
