/** MSW Node server for Vitest component/integration tests. */
import { setupServer } from 'msw/node'
import { onboardingHandlers } from './onboardingHandlers'

export const server = setupServer(...onboardingHandlers)
