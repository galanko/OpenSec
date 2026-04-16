import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'
import { queryClient } from '@/lib/query-client'
import { router } from '@/router'
import './index.css'

/**
 * In dev, stand up the MSW service worker so the onboarding wizard, dashboard,
 * and findings pages work without a backend. Production skips this entirely.
 * Set `VITE_USE_REAL_API=1` (or `VITE_MSW=off`) in dev to bypass MSW and hit
 * the FastAPI proxy. Session G removes the dev-time MSW once the eight real
 * routes are fully wired.
 */
async function startMockApi(): Promise<void> {
  if (!import.meta.env.DEV) return
  if (import.meta.env.VITE_USE_REAL_API) return
  if (import.meta.env.VITE_MSW === 'off') return
  try {
    const { worker } = await import('@/mocks/browser')
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: '/mockServiceWorker.js' },
    })
  } catch (err) {
    // Non-fatal: fall through to rendering so the app still boots.
    console.error('MSW worker failed to start', err)
  }
}

function renderApp() {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </StrictMode>,
  )
}

void startMockApi().finally(renderApp)
