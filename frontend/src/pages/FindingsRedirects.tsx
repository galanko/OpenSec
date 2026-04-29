/**
 * Tiny redirect components that mirror the legacy /findings* routes onto
 * their PRD-0006 Phase 1 /issues* counterparts. Lives in its own file so
 * router.tsx can stay HMR-friendly (react-refresh rule).
 */
import { Navigate, useParams } from 'react-router'

export function FindingDetailPageRedirect() {
  const { id } = useParams()
  return <Navigate to={`/issues/${id ?? ''}`} replace />
}
