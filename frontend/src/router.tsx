import { createBrowserRouter, Navigate } from 'react-router'
import AppLayout from '@/layouts/AppLayout'
import FindingsPage from '@/pages/FindingsPage'
import WorkspacePage from '@/pages/WorkspacePage'
import HistoryPage from '@/pages/HistoryPage'
import SettingsPage from '@/pages/SettingsPage'
import Spike from '@/pages/Spike'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <FindingsPage /> },
      { path: 'findings', element: <FindingsPage /> },
      { path: 'queue', element: <Navigate to="/findings" replace /> },
      { path: 'workspace/:id?', element: <WorkspacePage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'integrations', element: <Navigate to="/settings" replace /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'spike', element: <Spike /> },
    ],
  },
])
