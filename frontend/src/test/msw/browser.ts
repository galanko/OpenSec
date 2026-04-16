/** MSW Service Worker for the dev browser.
 * Registered from `src/main.tsx` when running in dev without the backend.
 */
import { setupWorker } from 'msw/browser'
import { onboardingHandlers } from './onboardingHandlers'

export const worker = setupWorker(...onboardingHandlers)
