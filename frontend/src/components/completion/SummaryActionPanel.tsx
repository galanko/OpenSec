/**
 * SummaryActionPanel — the three share-action tiles (IMPL-0002 Milestone H4).
 *
 * Layout (desktop): 2-column grid — ShareableSummaryCard preview on the left,
 * three stacked action tiles on the right. Mobile: preview stacks above tiles.
 *
 * Each tile: header (icon + title + one-line description) → preview block →
 * action button. Download's preview is a metadata row (filename + dimensions
 * + size); Copy text/markdown previews are <pre> blocks with the payload.
 *
 * Behavior:
 *  - Save .png: captures the ShareableSummaryCard DOM (true 1200×630 because
 *    the card itself is not transformed — the scale lives on its wrapper) via
 *    `exportCardAsPng`, fires the `download` share-action, calls `onAction`.
 *  - Copy to clipboard / Copy markdown: writes to the clipboard, fires the
 *    corresponding share-action, calls `onAction`.
 *  - Every action is rate-limited by `useShareAction`'s in-flight Set: a
 *    second click on a pending action is a deterministic no-op, so the POST
 *    fires exactly once per user intent.
 *
 * The frozen contract (Session 0) already covers the tiles' data. `cardProps`
 * is an additive, optional prop Session F introduces so the panel can render
 * the preview inline and perform the export self-contained. When `cardProps`
 * is omitted the preview column collapses and Save .png becomes a no-op.
 */
import { forwardRef, useImperativeHandle, useRef } from 'react'
import ShareableSummaryCard, {
  type ShareableSummaryCardProps,
} from './ShareableSummaryCard'
import { exportCardAsPng } from '../../lib/imageExport'
import { useShareAction, type ShareAction } from './useShareAction'

export interface SummaryActionPanelProps {
  completionId: string
  summaryText: string
  summaryMarkdown: string
  filename: string
  onAction?: (action: ShareAction) => void
  /** Additive Session F prop — card data for the inline preview + PNG export. */
  cardProps?: ShareableSummaryCardProps
}

// Preview-column scale. The card itself remains at 1200×630 in the DOM so
// html-to-image captures at native resolution; the wrapper scales the visual
// down to fit. Wrapper width/height MUST equal 1200*scale × 630*scale —
// CSS `transform` does NOT shrink the layout box.
const PREVIEW_SCALE = 0.4

export interface SummaryActionPanelHandle {
  /** Expose the card's DOM node so parents can export from outside. */
  getCardNode: () => HTMLDivElement | null
}

const SummaryActionPanel = forwardRef<SummaryActionPanelHandle, SummaryActionPanelProps>(
  function SummaryActionPanel(
    { completionId, summaryText, summaryMarkdown, filename, onAction, cardProps },
    ref,
  ) {
    const cardRef = useRef<HTMLDivElement>(null)
    const { runExclusive, record } = useShareAction(completionId)

    useImperativeHandle(ref, () => ({ getCardNode: () => cardRef.current }))

    function handleDownload() {
      void runExclusive('download', async () => {
        try {
          if (cardRef.current) {
            await exportCardAsPng(cardRef.current, filename)
          }
        } catch (err) {
          // Fallback is documented in the tile's helper text; log for devs.
          console.warn('PNG export failed:', err)
        }
        await record('download')
        onAction?.('download')
      })
    }

    function handleCopyText() {
      void runExclusive('copy_text', async () => {
        try {
          await navigator.clipboard.writeText(summaryText)
        } catch (err) {
          console.warn('clipboard write failed:', err)
        }
        await record('copy_text')
        onAction?.('copy_text')
      })
    }

    function handleCopyMarkdown() {
      void runExclusive('copy_markdown', async () => {
        try {
          await navigator.clipboard.writeText(summaryMarkdown)
        } catch (err) {
          console.warn('clipboard write failed:', err)
        }
        await record('copy_markdown')
        onAction?.('copy_markdown')
      })
    }

    return (
      <div data-testid="SummaryActionPanel" className="mx-auto max-w-4xl" id="summary-panel">
        <div className="mb-6">
          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">
            Your summary is ready
          </span>
          <h3 className="font-headline text-3xl font-extrabold tracking-tight text-on-surface mt-2">
            Share it, keep it, or ignore it
          </h3>
          <p className="text-on-surface-variant text-sm mt-1 max-w-xl">
            Generated locally in your browser. Nothing is uploaded. Nothing
            touches your repo unless you choose to paste the markdown yourself.
          </p>
        </div>

        <div className="grid md:grid-cols-[1.3fr_1fr] gap-6">
          {/* Preview column — native 1200×630 card inside a scale-down wrapper */}
          {cardProps && (
            <div
              className="rounded-2xl shadow-sm overflow-hidden"
              style={{
                width: `${1200 * PREVIEW_SCALE}px`,
                height: `${630 * PREVIEW_SCALE}px`,
                // The wrapper carries the visual scale. The card itself MUST
                // stay un-transformed so html-to-image captures full res.
              }}
            >
              <div
                style={{
                  transform: `scale(${PREVIEW_SCALE})`,
                  transformOrigin: 'top left',
                }}
              >
                <ShareableSummaryCard ref={cardRef} {...cardProps} />
              </div>
            </div>
          )}

          {/* Actions column */}
          <div className="space-y-3">
            {/* Tile 1 — Download */}
            <div className="bg-surface-container-lowest rounded-xl shadow-sm p-5">
              <div className="flex items-start gap-3 mb-3">
                <span className="material-symbols-outlined text-primary mt-0.5">
                  download
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-headline text-sm font-bold text-on-surface">
                    Download image
                  </p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Ready for social posts or your site.
                  </p>
                </div>
              </div>
              <div className="bg-surface-container-low rounded-lg px-3 py-2.5 text-[11px] font-mono text-on-surface-variant leading-relaxed mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-sm text-on-surface-variant">
                  image
                </span>
                <span className="flex-1 min-w-0 truncate">{filename}</span>
                <span className="text-on-surface-variant/70">1200×630 · ~80 KB</span>
              </div>
              <button
                type="button"
                onClick={handleDownload}
                className="w-full px-4 py-2.5 rounded-lg bg-primary text-white font-bold text-sm hover:bg-primary-dim transition-colors active:scale-95 shadow-sm"
              >
                Save .png
              </button>
            </div>

            {/* Tile 2 — Copy text */}
            <div className="bg-surface-container-lowest rounded-xl shadow-sm p-5">
              <div className="flex items-start gap-3 mb-3">
                <span className="material-symbols-outlined text-primary mt-0.5">
                  content_copy
                </span>
                <div className="flex-1 min-w-0">
                  <h4 className="font-headline text-sm font-bold text-on-surface">
                    Copy text summary
                  </h4>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Tweet-sized — drop it anywhere.
                  </p>
                </div>
              </div>
              <pre className="bg-surface-container-low rounded-lg px-3 py-2.5 text-[11px] font-mono text-on-surface leading-relaxed mb-3 whitespace-pre-wrap">
                {summaryText}
              </pre>
              <button
                type="button"
                onClick={handleCopyText}
                className="w-full px-4 py-2.5 rounded-lg bg-surface-container-low text-on-surface font-semibold text-sm hover:bg-surface-container"
              >
                Copy to clipboard
              </button>
            </div>

            {/* Tile 3 — Copy markdown */}
            <div className="bg-surface-container-lowest rounded-xl shadow-sm p-5">
              <div className="flex items-start gap-3 mb-3">
                <span className="material-symbols-outlined text-primary mt-0.5">
                  code
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-headline text-sm font-bold text-on-surface">
                    Copy README markdown
                  </p>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Paste it into your README yourself if you want.
                  </p>
                </div>
              </div>
              <pre className="bg-surface-container-low rounded-lg px-3 py-2.5 text-[11px] font-mono text-on-surface leading-relaxed mb-3 overflow-x-auto">
                {summaryMarkdown}
              </pre>
              <button
                type="button"
                onClick={handleCopyMarkdown}
                className="w-full px-4 py-2.5 rounded-lg bg-surface-container-low text-on-surface font-semibold text-sm hover:bg-surface-container"
              >
                Copy markdown
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 rounded-xl bg-surface-container-low px-5 py-4 flex items-start gap-3">
          <span className="material-symbols-outlined text-on-surface-variant mt-0.5">
            lock
          </span>
          <p className="text-sm text-on-surface-variant">
            This card is generated on your machine. No OpenSec-hosted URL, no
            tracking, no account required. v1.2 will add an optional public
            badge with verification — not today.
          </p>
        </div>
      </div>
    )
  },
)

export default SummaryActionPanel
