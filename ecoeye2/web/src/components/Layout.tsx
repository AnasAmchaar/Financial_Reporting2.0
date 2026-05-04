import { NavLink, Outlet } from 'react-router-dom'

const nav = [
  { to: '/insights', label: 'Insights', end: true },
  { to: '/ingest', label: 'Ingest', end: true },
  { to: '/data', label: 'Data' },
  { to: '/adjustments', label: 'Adjustments' },
  { to: '/visualize', label: 'Visualize' },
  { to: '/settings', label: 'Settings' },
]

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/20 text-lg font-bold text-emerald-300">
              E2
            </div>
            <div>
              <div className="text-lg font-semibold tracking-tight text-white">EcoEye2</div>
              <div className="text-xs text-slate-400">ETL · adjustments · insights</div>
            </div>
          </div>
          <span className="badge-muted">
            local
          </span>
        </div>
      </header>
      <nav className="flex border-b border-slate-800 bg-slate-950/70 px-2 py-2 md:hidden">
        <div className="flex flex-wrap gap-1">
          {nav.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `rounded px-2 py-1 text-xs ${isActive ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-400'}`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
      <div className="mx-auto flex w-full max-w-7xl flex-1 gap-0 px-0 md:px-2">
        <aside className="hidden w-52 shrink-0 p-3 md:block">
          <nav className="flex flex-col gap-1">
            {nav.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400'
                      : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
