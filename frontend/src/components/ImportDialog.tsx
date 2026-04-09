import { useCallback, useRef, useState } from 'react'
import { useStartIngest } from '@/api/hooks'
import IngestProgress from '@/components/IngestProgress'

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB

type Tab = 'upload' | 'paste'

interface ImportDialogProps {
  onComplete: () => void
  onClose: () => void
}

function guessSource(name: string): string {
  const lower = name.toLowerCase().replace(/\.json$/, '')
  for (const scanner of ['snyk', 'wiz', 'trivy', 'semgrep', 'checkov', 'prisma', 'sonarqube', 'grype', 'dependabot']) {
    if (lower.includes(scanner)) return scanner
  }
  return 'unknown'
}

export default function ImportDialog({ onComplete, onClose }: ImportDialogProps) {
  const [tab, setTab] = useState<Tab>('upload')
  const [jobId, setJobId] = useState<string | null>(null)
  const [source, setSource] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const startIngest = useStartIngest()

  // Once a job is started (from file upload), delegate to IngestProgress
  if (jobId) {
    return (
      <IngestProgress
        onComplete={onComplete}
        onClose={onClose}
        initialJobId={jobId}
        initialSource={source}
      />
    )
  }

  // Paste tab: delegate entirely to IngestProgress (its input state)
  if (tab === 'paste') {
    return (
      <IngestProgress
        onComplete={onComplete}
        onClose={onClose}
      />
    )
  }

  // --- Upload tab ---

  async function processFile(file: File) {
    setFileError(null)
    setFileName(file.name)

    if (file.size > MAX_FILE_SIZE) {
      setFileError(`File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum is 10MB.`)
      return
    }

    if (!file.name.endsWith('.json')) {
      setFileError('Only .json files are supported.')
      return
    }

    let text: string
    try {
      text = await file.text()
    } catch {
      setFileError('Could not read file.')
      return
    }

    let parsed: Record<string, unknown>[]
    try {
      const data = JSON.parse(text)
      if (!Array.isArray(data) || data.length === 0) {
        setFileError('File must contain a non-empty JSON array of findings.')
        return
      }
      parsed = data
    } catch {
      setFileError('Invalid JSON. The file must contain a valid JSON array.')
      return
    }

    const detectedSource = guessSource(file.name)
    setSource(detectedSource)

    try {
      const res = await startIngest.mutateAsync({
        source: detectedSource,
        raw_data: parsed,
      })
      setJobId(res.job_id)
    } catch (err) {
      setFileError(err instanceof Error ? err.message : 'Failed to start import.')
    }
  }

  return <UploadView
    onClose={onClose}
    onSwitchToPaste={() => setTab('paste')}
    dragOver={dragOver}
    setDragOver={setDragOver}
    fileInputRef={fileInputRef}
    fileError={fileError}
    fileName={fileName}
    isPending={startIngest.isPending}
    processFile={processFile}
  />
}

/** Upload tab UI — extracted to avoid TypeScript narrowing issues with early returns. */
function UploadView({
  onClose,
  onSwitchToPaste,
  dragOver,
  setDragOver,
  fileInputRef,
  fileError,
  fileName,
  isPending,
  processFile,
}: {
  onClose: () => void
  onSwitchToPaste: () => void
  dragOver: boolean
  setDragOver: (v: boolean) => void
  fileInputRef: React.RefObject<HTMLInputElement | null>
  fileError: string | null
  fileName: string | null
  isPending: boolean
  processFile: (file: File) => void
}) {
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }, [setDragOver, processFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [setDragOver])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
  }, [setDragOver])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
  }, [processFile])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px]"
      onClick={onClose}
    >
      <div
        className="bg-surface-container-lowest rounded-2xl shadow-xl w-full max-w-lg mx-4 overflow-hidden animate-in fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          {/* Header */}
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

          {/* Tabs */}
          <div className="flex gap-1 bg-surface-container-low rounded-lg p-1 mb-5">
            <button
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors bg-surface-container-lowest text-on-surface shadow-sm"
            >
              <span className="material-symbols-outlined text-sm">upload_file</span>
              Upload
            </button>
            <button
              onClick={onSwitchToPaste}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined text-sm">content_paste</span>
              Paste
            </button>
          </div>

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`rounded-xl py-12 px-6 flex flex-col items-center justify-center cursor-pointer transition-all ${
              dragOver
                ? 'bg-primary/5 ring-2 ring-primary/20'
                : 'bg-surface-container-low hover:bg-surface-container'
            } ${isPending ? 'pointer-events-none opacity-60' : ''}`}
            style={{ border: '2px dashed', borderColor: dragOver ? 'var(--color-primary, #4d44e3)' : 'rgba(190,195,198,0.3)' }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileChange}
            />

            {isPending ? (
              <>
                <span className="material-symbols-outlined text-3xl text-primary animate-spin mb-3">
                  progress_activity
                </span>
                <p className="text-sm font-semibold text-on-surface">
                  Starting import...
                </p>
                {fileName && (
                  <p className="text-xs text-on-surface-variant mt-1">{fileName}</p>
                )}
              </>
            ) : (
              <>
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <span className="material-symbols-outlined text-2xl text-primary">
                    upload_file
                  </span>
                </div>
                <p className="text-sm font-semibold text-on-surface mb-1">
                  Drop a JSON file here, or click to browse
                </p>
                <p className="text-xs text-on-surface-variant">
                  Accepts .json up to 10MB
                </p>
              </>
            )}
          </div>

          {/* File error */}
          {fileError && (
            <div className="bg-red-50 text-red-800 rounded-lg px-4 py-3 text-sm mt-4">
              {fileError}
            </div>
          )}

          {/* Footer */}
          <p className="text-xs text-on-surface-variant text-center mt-5">
            Tested with Snyk, Wiz, and generic JSON formats
          </p>

          {/* Actions */}
          <div className="flex justify-end mt-5">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-on-surface-variant hover:text-on-surface rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
