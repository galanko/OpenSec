/**
 * MSW server for vitest + Node environment. Registers handlers from every
 * Session that ships its own MSW slice (dashboard + completion from Sessions
 * E + F, onboarding from Session D). Session G consolidates these once the
 * real backend lands.
 *
 * Browser counterpart lives in `browser.ts` (started from main.tsx in dev only).
 */

import { setupServer } from 'msw/node'
import { onboardingHandlers } from '@/test/msw/onboardingHandlers'
import { handlers } from './handlers'

export const server = setupServer(...handlers, ...onboardingHandlers)
