import { NavLink } from 'react-router'

/**
 * Primary navigation rail (PRD-0004 Story 0 + Story 2; trimmed in PRD-0006
 * Phase 1).
 *
 * Phase 1 destinations: Dashboard + Issues. Settings is anchored to the
 * bottom via ``mt-auto``. Workspace and History are reachable via direct URL
 * (the routes still resolve) but no longer have nav entries — they're
 * contextual surfaces in the alpha cut.
 *
 * Active indicator is tonal only (``bg-primary/12`` pill + ``text-primary``)
 * — no 1px borders, per Serene Sentinel (ADR-0011).
 */

const primaryItems = [
  { to: '/dashboard', icon: 'speed', title: 'Dashboard' },
  { to: '/issues', icon: 'inbox', title: 'Issues' },
]

const activeClass =
  'p-3 rounded-xl text-primary bg-primary/12 font-semibold transition-all duration-200'
const inactiveClass =
  'p-3 rounded-xl text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all duration-200'
const focusRing =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-0'

export default function SideNav() {
  return (
    <aside className="fixed left-0 top-0 h-full w-20 bg-surface-container-low flex flex-col items-center py-6 gap-y-4 z-50">
      <NavLink
        to="/dashboard"
        aria-label="OpenSec home"
        className={`w-10 h-10 rounded-xl bg-surface-container-lowest shadow-sm flex items-center justify-center mb-2 ${focusRing}`}
      >
        <span className="text-xl font-bold text-on-surface tracking-tighter">
          O
        </span>
      </NavLink>
      <nav
        aria-label="Primary"
        className="flex flex-col items-center gap-y-2 w-full"
      >
        {primaryItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={item.title}
            aria-label={item.title}
            className={({ isActive }) =>
              `${isActive ? activeClass : inactiveClass} ${focusRing}`
            }
          >
            <span className="material-symbols-outlined" aria-hidden>
              {item.icon}
            </span>
          </NavLink>
        ))}
      </nav>
      <NavLink
        to="/settings"
        title="Settings"
        aria-label="Settings"
        className={({ isActive }) =>
          `mt-auto ${isActive ? activeClass : inactiveClass} ${focusRing}`
        }
      >
        <span className="material-symbols-outlined" aria-hidden>
          settings
        </span>
      </NavLink>
    </aside>
  )
}
