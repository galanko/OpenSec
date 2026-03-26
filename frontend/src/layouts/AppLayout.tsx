import { Outlet } from 'react-router'
import SideNav from '@/components/layout/SideNav'
import TopBar from '@/components/layout/TopBar'

export default function AppLayout() {
  return (
    <div className="overflow-x-hidden">
      <SideNav />
      <TopBar />
      <main className="ml-20 min-h-[calc(100vh-4rem)]">
        <Outlet />
      </main>
    </div>
  )
}
