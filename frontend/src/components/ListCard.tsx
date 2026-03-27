interface ListCardProps {
  children: React.ReactNode
  className?: string
}

export default function ListCard({ children, className }: ListCardProps) {
  return (
    <div
      className={`bg-surface-container-lowest rounded-xl p-5 border border-transparent hover:shadow-md hover:border-primary/5 transition-all duration-200 flex flex-col md:flex-row md:items-center gap-4 ${className ?? ''}`}
    >
      {children}
    </div>
  )
}
