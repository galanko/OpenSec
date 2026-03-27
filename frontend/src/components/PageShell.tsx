interface PageShellProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  children: React.ReactNode
}

export default function PageShell({ title, subtitle, actions, children }: PageShellProps) {
  return (
    <div className="px-8 lg:px-12 pt-6 pb-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-on-surface mb-2">
              {title}
            </h1>
            {subtitle && (
              <p className="text-on-surface-variant max-w-lg">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex items-center gap-x-3">{actions}</div>}
        </div>
        {children}
      </div>
    </div>
  )
}
