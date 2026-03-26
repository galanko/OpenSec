import Markdown from './Markdown'

interface ResultCardProps {
  agentName: string
  resultId: string
  content: string
  confidence?: number
  onAccept?: () => void
  onDismiss?: () => void
}

export default function ResultCard({ agentName, resultId, content, confidence, onAccept, onDismiss }: ResultCardProps) {
  return (
    <div className="bg-white rounded-2xl shadow-md overflow-hidden border border-surface-container/80">
      <div className="bg-primary/5 px-6 py-3 border-b border-surface-container/50 flex items-center justify-between">
        <h3 className="text-sm font-bold text-primary tracking-tight">{agentName}</h3>
        <div className="flex items-center gap-3">
          {confidence != null && (
            <span className="text-[10px] font-bold text-primary-dim">
              {Math.round(confidence * 100)}% confidence
            </span>
          )}
          <span className="text-[10px] font-bold text-on-surface-variant uppercase bg-surface-container-high px-2 py-0.5 rounded">
            {resultId}
          </span>
        </div>
      </div>
      <div className="p-6">
        <Markdown content={content} />
        {(onAccept || onDismiss) && (
          <div className="mt-6 flex gap-3">
            {onAccept && (
              <button
                onClick={onAccept}
                className="bg-primary text-white text-xs font-bold px-4 py-2 rounded-lg hover:shadow-lg hover:shadow-primary/20 transition-all"
              >
                Accept
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="text-on-surface-variant text-xs font-bold px-4 py-2 rounded-lg border border-outline-variant/30 hover:bg-surface-container-low transition-all"
              >
                Dismiss
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
