/**
 * PNG export for the `ShareableSummaryCard`.
 *
 * Why toBlob and not toPng:
 *  - `toPng` produces a data URL which hits a ~2MB ceiling in some Safari
 *    versions; a 1200×630 @ 2x PNG can exceed that.
 *  - `toBlob` + `URL.createObjectURL` is more memory-efficient and matches
 *    IMPL-0002 H5's explicit Safari mitigation guidance.
 *
 * Why the dynamic import:
 *  - `html-to-image` is ~80KB gzipped. It only runs when the user clicks
 *    Download, so we load it on demand and keep it out of first-paint.
 *
 * Why `document.fonts.ready`:
 *  - In Safari (and sporadically other browsers) the card can rasterize
 *    before custom fonts (Manrope/Inter) finish loading, producing a PNG
 *    with a fallback font. Waiting for `document.fonts.ready` eliminates
 *    that race.
 *
 * Callers can catch `ExportError` and surface a right-click-to-save
 * fallback toast if anything goes wrong.
 */

type ExportErrorReason = 'ref-null' | 'blob-null' | 'render-failed'

export class ExportError extends Error {
  readonly reason: ExportErrorReason

  constructor(reason: ExportErrorReason, message?: string) {
    super(message ?? reason)
    this.name = 'ExportError'
    this.reason = reason
  }
}

export async function exportCardAsPng(
  node: HTMLElement | null,
  filename: string,
): Promise<void> {
  if (!node) {
    throw new ExportError('ref-null', 'Source node was null — nothing to export')
  }

  // Wait for fonts before capture (Safari font-flash mitigation).
  if (typeof document !== 'undefined' && document.fonts?.ready) {
    await document.fonts.ready
  }

  const { toBlob } = await import('html-to-image')

  // First pass: try a full render with embedded fonts. If the browser refuses
  // to read cross-origin CSS rules from Google Fonts (Firefox is strict here,
  // Chromium + WebKit degrade gracefully), fall back to a font-skipped render.
  // The fallback uses system fonts and still produces a valid, non-empty PNG
  // — slightly off-brand but the download never silently fails.
  let blob: Blob | null = null
  const baseOpts = {
    width: 1200,
    height: 630,
    pixelRatio: 2,
    cacheBust: true,
  }
  try {
    blob = await toBlob(node, baseOpts)
  } catch {
    // Proceed to the skipFonts retry below.
  }
  if (!blob) {
    try {
      blob = await toBlob(node, { ...baseOpts, skipFonts: true })
    } catch (err) {
      throw new ExportError('render-failed', (err as Error).message)
    }
  }
  if (!blob) {
    throw new ExportError('blob-null', 'toBlob returned null')
  }

  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  // Revoke on the next tick so the download has a chance to start.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
