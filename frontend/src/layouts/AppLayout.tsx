import { Outlet } from 'react-router'
import SideNav from '@/components/layout/SideNav'

/**
 * App chrome — fixed ``SideNav`` on the left, ``<Outlet />`` for the page.
 *
 * PRD-0004 Story 0 retires ``TopBar`` entirely: its only tenants (search,
 * notifications bell, help) were non-functional placeholders. Each page
 * component now owns its own title row via ``PageShell``.
 *
 * ``overflow-x-clip`` on the outer div + ``overflow-x-hidden`` on the
 * scrolling column preserve the B10 dogfood fix — long strings inside a
 * posture card (branch-protection API responses, etc.) can't widen the page.
 */
export default function AppLayout() {
  return (
    <div className="flex min-h-screen overflow-x-clip">
      <SideNav />
      <main className="ml-20 flex-1 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  )
}
