import { NavLink } from 'react-router'
import { useHealth } from '@/api/hooks'

const topNavLinks = [
  { to: '/findings', label: 'Findings' },
  { to: '/workspace', label: 'Workspace' },
  { to: '/history', label: 'History' },
]

export default function TopBar() {
  const { data: health } = useHealth()

  return (
    <header className="sticky top-0 z-40 bg-surface-container-lowest/80 backdrop-blur-xl shadow-sm shadow-outline-variant/10 ml-20 w-[calc(100%-5rem)] flex justify-between items-center px-8 h-16">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <span className="text-lg font-extrabold tracking-tight text-on-surface">OpenSec</span>
          {health && (
            <span
              className={`w-2 h-2 rounded-full ${health.opencode === 'running' ? 'bg-green-500' : 'bg-outline-variant'}`}
              title={`Engine: ${health.opencode}`}
            />
          )}
        </div>
        <nav className="hidden md:flex items-center gap-6">
          {topNavLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                isActive
                  ? 'text-primary font-semibold border-b-2 border-primary py-5 transition-colors'
                  : 'text-on-surface-variant font-medium hover:text-primary transition-colors py-5'
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <div className="relative hidden sm:block">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">
            search
          </span>
          <input
            className="bg-surface-container-low border-none rounded-lg pl-10 pr-4 py-1.5 text-sm w-64 focus:ring-2 focus:ring-primary/20 transition-all"
            placeholder="Search findings..."
            type="text"
          />
        </div>
        <button className="p-2 text-on-surface-variant hover:bg-surface-container transition-colors rounded-full">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="p-2 text-on-surface-variant hover:bg-surface-container transition-colors rounded-full">
          <span className="material-symbols-outlined">help_outline</span>
        </button>
      </div>
    </header>
  )
}
