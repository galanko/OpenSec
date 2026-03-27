import { NavLink } from 'react-router'

const navItems = [
  { to: '/queue', icon: 'assignment_late', title: 'Queue' },
  { to: '/workspace', icon: 'terminal', title: 'Workspace' },
  { to: '/history', icon: 'history', title: 'History' },
]

export default function SideNav() {
  return (
    <aside className="fixed left-0 top-0 h-full w-20 border-r border-outline-variant/20 bg-surface-container-low flex flex-col items-center py-8 gap-y-6 z-50">
      <div className="mb-4">
        <span className="text-xl font-bold text-on-surface tracking-tighter">O</span>
      </div>
      <nav className="flex flex-col items-center gap-y-4 w-full">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.title}
            className={({ isActive }) =>
              isActive
                ? 'p-3 rounded-xl text-primary border-r-2 border-primary bg-primary-container/30 transition-all duration-200 scale-95'
                : 'p-3 rounded-xl text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all duration-200'
            }
          >
            <span className="material-symbols-outlined">{item.icon}</span>
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto flex flex-col items-center gap-y-4">
        <NavLink
          to="/settings"
          title="Settings"
          className={({ isActive }) =>
            isActive
              ? 'p-3 rounded-xl text-primary border-r-2 border-primary bg-primary-container/30 transition-all duration-200'
              : 'p-3 rounded-xl text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all duration-200'
          }
        >
          <span className="material-symbols-outlined">settings</span>
        </NavLink>
        <div className="w-10 h-10 rounded-full bg-surface-container-highest overflow-hidden flex items-center justify-center">
          <span className="text-xs font-bold text-on-surface-variant">GA</span>
        </div>
      </div>
    </aside>
  )
}
