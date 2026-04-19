import { Outlet } from 'react-router'
import SideNav from '@/components/layout/SideNav'
import TopBar from '@/components/layout/TopBar'

/**
 * App chrome — fixed `SideNav` on the left, sticky `TopBar` at the top,
 * `<Outlet />` for the page content.
 *
 * Dogfood flagged (bug B10) that long dashboard content — the expanded
 * posture card can reach ~1900px tall once every failing check is open
 * with its "How to fix" instructions — interacted weirdly with the old
 * layout. Two concrete issues were in the original:
 *
 * 1. The outer `<div>` used `overflow-x-clip` alone (no height or
 *    flex-direction), so it behaved like `display: block` inside the
 *    implicit document flow. When the main column grew past the
 *    viewport, horizontal-overflow guarantees from a posture card's
 *    long URL or detail line (e.g. a branch-protection API response)
 *    could escape and create a stray horizontal scrollbar on mobile.
 * 2. `main` had `min-h-[calc(100vh-4rem)]` but no `overflow-x-hidden`,
 *    so the same long strings could widen the page and push `TopBar`
 *    out of alignment with the content column.
 *
 * New structure is an explicit flex column that stretches to the full
 * viewport height, with `overflow-x-hidden` on the scrolling column so
 * nothing inside a page body can break the horizontal axis. Visual
 * output is identical to the prior layout for all in-viewport content;
 * only the edge cases change.
 */
export default function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-clip">
      <SideNav />
      <TopBar />
      <main className="ml-20 flex-1 overflow-x-hidden">
        <Outlet />
      </main>
    </div>
  )
}
