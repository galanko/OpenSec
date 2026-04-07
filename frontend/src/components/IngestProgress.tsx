import { useCallback, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { api, type IngestJobStatus } from '@/api/client'
import { useCancelIngest, useIngestProgress, useStartIngest } from '@/api/hooks'

interface IngestProgressProps {
  onComplete: () => void
  onClose: () => void
}

export default function IngestProgress({ onComplete, onClose }: IngestProgressProps) {
  const [source, setSource] = useState('')
  const [rawJson, setRawJson] = useState('')
  const [parseError, setParseError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [estimate, setEstimate] = useState<{
    total_items: number
    total_chunks: number
    estimated_tokens: number | null
  } | null>(null)
  const [estimating, setEstimating] = useState(false)
  const startedAtRef = useRef<number | null>(null)
  const [elapsed, setElapsed] = useState(0)

  const startIngest = useStartIngest()
  const cancelIngest = useCancelIngest()
  const { data: progress } = useIngestProgress(jobId)
  const qc = useQueryClient()

  // Track elapsed time while running
  useEffect(() => {
    if (!jobId || !progress) return
    if (progress.status === 'pending' || progress.status === 'processing') {
      if (!startedAtRef.current) startedAtRef.current = Date.now()
      const timer = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startedAtRef.current!) / 1000))
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [jobId, progress])

  // Invalidate findings on terminal states
  useEffect(() => {
    if (!progress) return
    if (progress.status === 'completed' || progress.status === 'cancelled') {
      qc.invalidateQueries({ queryKey: ['findings'] })
    }
  }, [progress, qc])

  const handleEstimate = useCallback(async (json: string, src: string) => {
    if (!json.trim() || !src.trim()) {
      setEstimate(null)
      return
    }
    try {
      const parsed = JSON.parse(json)
      if (!Array.isArray(parsed) || parsed.length === 0) return
      setEstimating(true)
      const res = await api.startIngest({ source: src, raw_data: parsed, dry_run: true })
      setEstimate({
        total_items: res.total_items,
        total_chunks: res.total_chunks,
        estimated_tokens: res.estimated_tokens,
      })
    } catch {
      // Estimation is best-effort — ignore errors
    } finally {
      setEstimating(false)
    }
  }, [])

  const handleStart = useCallback(async () => {
    setParseError(null)
    let parsed: Record<string, unknown>[]
    try {
      const data = JSON.parse(rawJson)
      if (!Array.isArray(data) || data.length === 0) {
        setParseError('Input must be a non-empty JSON array.')
        return
      }
      parsed = data
    } catch {
      setParseError('Invalid JSON. Paste a JSON array of findings from your scanner.')
      return
    }

    try {
      const res = await startIngest.mutateAsync({ source, raw_data: parsed })
      setJobId(res.job_id)
      startedAtRef.current = Date.now()
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Failed to start import.')
    }
  }, [rawJson, source, startIngest])

  const handleCancel = useCallback(() => {
    if (jobId) cancelIngest.mutate(jobId)
  }, [jobId, cancelIngest])

  const handleDone = useCallback(() => {
    onComplete()
  }, [onComplete])

  const handleReset = useCallback(() => {
    setJobId(null)
    setEstimate(null)
    setParseError(null)
    startedAtRef.current = null
    setElapsed(0)
  }, [])

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`
  }

  const formatTokens = (n: number) => {
    if (n >= 1000) return `~${(n / 1000).toFixed(1)}k`
    return `~${n}`
  }

  // Determine which state to render
  const status: IngestJobStatus | 'input' = jobId && progress ? progress.status : 'input'

  return (
    <div className="bg-surface-container-lowest rounded-xl shadow-sm shadow-slate-200/50 mb-6 overflow-hidden">
      {/* Terminal state header strips */}
      {status === 'completed' && (
        <div className="bg-green-50 px-6 py-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-green-700">check_circle</span>
          <span className="text-sm font-semibold text-green-800">Import complete</span>
        </div>
      )}
      {status === 'failed' && (
        <div className="bg-red-50 px-6 py-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-error">error</span>
          <span className="text-sm font-semibold text-red-800">Import failed</span>
        </div>
      )}
      {status === 'cancelled' && (
        <div className="bg-surface-container-low px-6 py-3 flex items-center gap-2">
          <span className="material-symbols-outlined text-base text-on-surface-variant">cancel</span>
          <span className="text-sm font-semibold text-on-surface-variant">Import cancelled</span>
        </div>
      )}

      <div className="p-6">
        {/* --- INPUT STATE --- */}
        {status === 'input' && (
          <>
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-headline text-base font-bold text-on-surface tracking-tight">
                Import findings
              </h3>
              <button
                onClick={onClose}
                className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-md transition-colors"
              >
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-on-surface-variant block mb-1">
                  Source name
                </label>
                <input
                  type="text"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  placeholder="e.g. wiz, snyk, trivy"
                  className="w-full bg-surface-container-low rounded-lg px-3 py-2 text-sm text-on-surface outline-none focus:ring-2 focus:ring-primary/20 placeholder:text-outline-variant"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-on-surface-variant block mb-1">
                  Raw findings (JSON array)
                </label>
                <textarea
                  value={rawJson}
                  onChange={(e) => {
                    setRawJson(e.target.value)
                    setParseError(null)
                  }}
                  onBlur={() => handleEstimate(rawJson, source)}
                  placeholder={'[\n  { "id": "...", "title": "...", "severity": "..." },\n  ...\n]'}
                  className="w-full bg-surface-container-low rounded-lg px-3 py-2.5 text-sm font-mono text-on-surface outline-none focus:ring-2 focus:ring-primary/20 placeholder:text-outline-variant min-h-[120px] resize-y"
                />
              </div>

              {parseError && (
                <div className="bg-red-50 text-red-800 rounded-lg px-4 py-3 text-sm">
                  {parseError}
                </div>
              )}

              {estimate && !parseError && (
                <div className="bg-surface-container-low rounded-lg px-4 py-2.5 flex items-center gap-2">
                  <span className="material-symbols-outlined text-sm text-on-surface-variant">
                    {estimating ? 'progress_activity' : 'token'}
                  </span>
                  <span className="text-xs text-on-surface-variant">
                    {estimate.total_items} findings in {estimate.total_chunks} chunks
                    {estimate.estimated_tokens != null && (
                      <>, {formatTokens(estimate.estimated_tokens)} tokens</>
                    )}
                  </span>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-semibold text-on-surface-variant hover:text-on-surface rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={!source.trim() || !rawJson.trim() || startIngest.isPending}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary-dim transition-colors disabled:opacity-40 active:scale-95 shadow-sm shadow-primary/10"
              >
                {startIngest.isPending ? 'Starting...' : 'Import'}
              </button>
            </div>
          </>
        )}

        {/* --- RUNNING STATE (pending + processing) --- */}
        {(status === 'pending' || status === 'processing') && progress && (
          <>
            <div className="flex items-center gap-2 mb-4">
              <span className="material-symbols-outlined text-sm text-primary animate-spin">
                progress_activity
              </span>
              <span className="text-sm font-semibold text-on-surface">
                Processing {progress.total_items} findings...
              </span>
              <span className="text-xs text-on-surface-variant ml-auto">
                {formatElapsed(elapsed)}
              </span>
            </div>

            {/* Progress bar */}
            <div className="w-full h-1.5 bg-surface-container rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-700 ease-out"
                style={{
                  width: `${progress.total_chunks > 0
                    ? Math.round((progress.completed_chunks / progress.total_chunks) * 100)
                    : 0}%`,
                }}
              />
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div>
                <div className="text-lg font-bold text-on-surface font-headline">
                  {progress.findings_created}
                </div>
                <div className="text-xs text-on-surface-variant">findings created</div>
              </div>
              <div>
                <div className="text-lg font-bold text-on-surface font-headline">
                  {progress.completed_chunks}/{progress.total_chunks}
                </div>
                <div className="text-xs text-on-surface-variant">chunks processed</div>
              </div>
              <div>
                <div className={`text-lg font-bold font-headline ${progress.failed_chunks > 0 ? 'text-error' : 'text-on-surface'}`}>
                  {progress.failed_chunks}
                </div>
                <div className="text-xs text-on-surface-variant">errors</div>
              </div>
            </div>

            <div className="flex justify-end mt-4">
              <button
                onClick={handleCancel}
                disabled={cancelIngest.isPending}
                className="text-xs font-semibold text-on-surface-variant hover:text-error transition-colors"
              >
                Cancel import
              </button>
            </div>
          </>
        )}

        {/* --- COMPLETED STATE --- */}
        {status === 'completed' && progress && (
          <>
            <p className="text-sm text-on-surface">
              <strong className="font-semibold">{progress.findings_created}</strong>
              {' findings imported from '}
              <strong className="font-semibold">{source}</strong>
              {' in '}
              {formatElapsed(elapsed)}
            </p>

            {progress.failed_chunks > 0 && (
              <p className="mt-2 text-xs text-on-surface-variant">
                {progress.failed_chunks} chunk{progress.failed_chunks > 1 ? 's' : ''} had errors
                {' \u2014 '}
                {progress.total_items - progress.findings_created} findings could not be parsed.
              </p>
            )}

            {progress.errors.length > 0 && (
              <ErrorList errors={progress.errors} />
            )}

            <div className="flex justify-end mt-4">
              <button
                onClick={handleDone}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary-dim transition-colors active:scale-95"
              >
                Done
              </button>
            </div>
          </>
        )}

        {/* --- FAILED STATE --- */}
        {status === 'failed' && progress && (
          <>
            <p className="text-sm text-on-surface mb-3">
              All chunks failed to process. This usually means the model could not parse the input format.
            </p>

            {progress.errors.length > 0 && (
              <ErrorList errors={progress.errors} />
            )}

            <div className="flex justify-end gap-3 mt-4">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-semibold text-on-surface-variant hover:text-on-surface rounded-lg transition-colors"
              >
                Close
              </button>
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary-dim transition-colors active:scale-95"
              >
                Try again
              </button>
            </div>
          </>
        )}

        {/* --- CANCELLED STATE --- */}
        {status === 'cancelled' && progress && (
          <>
            <p className="text-sm text-on-surface">
              {progress.findings_created > 0 ? (
                <>
                  <strong className="font-semibold">{progress.findings_created}</strong>
                  {' findings were imported before cancellation.'}
                </>
              ) : (
                'Import was cancelled before any findings were created.'
              )}
            </p>

            <div className="flex justify-end mt-4">
              <button
                onClick={handleDone}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg text-sm font-semibold hover:bg-primary-dim transition-colors active:scale-95"
              >
                Done
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function ErrorList({ errors }: { errors: string[] }) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? errors : errors.slice(0, 3)
  const hasMore = errors.length > 3

  return (
    <div className="mt-3">
      <div className="bg-surface-container-low rounded-lg max-h-32 overflow-y-auto">
        {visible.map((err, i) => (
          <div
            key={i}
            className="px-4 py-2 text-xs font-mono text-on-surface-variant border-b border-outline-variant/10 last:border-b-0"
          >
            {err}
          </div>
        ))}
      </div>
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-semibold text-primary hover:text-primary/80 transition-colors mt-1.5"
        >
          {expanded ? 'Show less' : `Show all ${errors.length} errors`}
        </button>
      )}
    </div>
  )
}
