import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it } from 'vitest'
import {
  dashboardApi,
  useDashboard,
  useFixPostureCheck,
} from '../dashboard'
import {
  gradeCWithIssuesPayload,
} from '../../mocks/fixtures/dashboard'

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    )
  }
}

describe('dashboardApi', () => {
  it('getDashboard hits /api/dashboard and returns the MSW fixture', async () => {
    const payload = await dashboardApi.getDashboard()
    expect(payload).toEqual(gradeCWithIssuesPayload)
  })
})

describe('useDashboard', () => {
  it('resolves with the MSW fixture', async () => {
    const { result } = renderHook(() => useDashboard(), { wrapper: wrapper() })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.grade).toBe('C')
  })
})

describe('useFixPostureCheck', () => {
  it('posts to /api/posture/fix/:checkName and returns workspace id', async () => {
    const { result } = renderHook(() => useFixPostureCheck(), {
      wrapper: wrapper(),
    })
    result.current.mutate('security_md')
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data?.check_name).toBe('security_md')
    expect(result.current.data?.workspace_id).toMatch(/^ws_/)
  })
})
