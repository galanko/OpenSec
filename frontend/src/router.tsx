import { createBrowserRouter, Navigate } from 'react-router'
import AppLayout from '@/layouts/AppLayout'
import FeatureFlagGate from '@/components/FeatureFlagGate'
import DashboardPage from '@/pages/DashboardPage'
import FindingDetailPage from '@/pages/FindingDetailPage'
import FindingsPage from '@/pages/FindingsPage'
import WorkspacePage from '@/pages/WorkspacePage'
import HistoryPage from '@/pages/HistoryPage'
import SettingsPage from '@/pages/SettingsPage'
import Spike from '@/pages/Spike'
import Welcome from '@/pages/onboarding/Welcome'
import ConnectRepo from '@/pages/onboarding/ConnectRepo'
import ConfigureAI from '@/pages/onboarding/ConfigureAI'
import StartAssessment from '@/pages/onboarding/StartAssessment'

const gated = (page: React.ReactElement) => (
  <FeatureFlagGate flag="v1_1_from_zero_to_secure_enabled">{page}</FeatureFlagGate>
)

export const router = createBrowserRouter([
  // Onboarding wizard — full-bleed, lives outside AppLayout per UX spec.
  { path: '/onboarding', element: <Navigate to="/onboarding/welcome" replace /> },
  { path: '/onboarding/welcome', element: gated(<Welcome />) },
  { path: '/onboarding/connect', element: gated(<ConnectRepo />) },
  { path: '/onboarding/ai', element: gated(<ConfigureAI />) },
  { path: '/onboarding/start', element: gated(<StartAssessment />) },

  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <FindingsPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'findings', element: <FindingsPage /> },
      { path: 'findings/:id', element: <FindingDetailPage /> },
      { path: 'queue', element: <Navigate to="/findings" replace /> },
      { path: 'workspace/:id?', element: <WorkspacePage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'integrations', element: <Navigate to="/settings" replace /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'spike', element: <Spike /> },
    ],
  },
])
