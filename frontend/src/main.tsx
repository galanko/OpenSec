import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router'
import { queryClient } from '@/lib/query-client'
import { router } from '@/router'
import './index.css'

/**
 * In dev, stand up the MSW service worker so the onboarding wizard works
 * without a backend. Production skips this entirely and renders synchronously.
 * Set `VITE_USE_REAL_API=1` in dev to bypass MSW and hit the FastAPI proxy.
 */
async function startMockApi(): Promise<void> {
  if (!import.meta.env.DEV || import.meta.env.VITE_USE_REAL_API) return
  try {
    const { worker } = await import('@/test/msw/browser')
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

if (import.meta.env.DEV && !import.meta.env.VITE_USE_REAL_API) {
  startMockApi().then(renderApp)
} else {
  renderApp()
}
