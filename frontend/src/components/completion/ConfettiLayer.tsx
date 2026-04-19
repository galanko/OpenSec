/**
 * ConfettiLayer — decorative burst for the completion celebration.
 *
 * 12 positioned `<span class="confetti">` elements (mix of rectangular and
 * circular particles, alternating primary/tertiary). Animation + reduced-
 * motion gating live in `index.css`. This component also short-circuits to
 * `null` under `prefers-reduced-motion: reduce` so the particles never hit
 * the DOM at all.
 *
 * Purely presentational — `aria-hidden` strips it from the a11y tree.
 */
import { usePrefersReducedMotion } from '../../lib/usePrefersReducedMotion'

// 12 particles — (left%, top%, delaySeconds, shape)
// Positions lifted verbatim from mockup frames/5.1 so the visual remains
// exactly what the design team approved.
const PARTICLES: Array<{
  left: string
  top: string
  delay: string
  color: 'primary' | 'tertiary'
  round: boolean
}> = [
  { left: '8%', top: '10%', delay: '0s', color: 'primary', round: false },
  { left: '18%', top: '20%', delay: '.3s', color: 'tertiary', round: true },
  { left: '28%', top: '6%', delay: '.6s', color: 'primary', round: false },
  { left: '42%', top: '14%', delay: '.2s', color: 'tertiary', round: false },
  { left: '56%', top: '22%', delay: '.9s', color: 'primary', round: true },
  { left: '68%', top: '8%', delay: '.5s', color: 'tertiary', round: false },
  { left: '82%', top: '18%', delay: '.1s', color: 'primary', round: false },
  { left: '92%', top: '26%', delay: '.7s', color: 'tertiary', round: true },
  { left: '12%', top: '30%', delay: '1.2s', color: 'primary', round: false },
  { left: '34%', top: '36%', delay: '1s', color: 'tertiary', round: false },
  { left: '60%', top: '32%', delay: '.8s', color: 'primary', round: false },
  { left: '78%', top: '40%', delay: '1.4s', color: 'tertiary', round: false },
]

export default function ConfettiLayer() {
  const reduced = usePrefersReducedMotion()
  if (reduced) return null

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      {PARTICLES.map((p, i) => {
        const base: React.CSSProperties = {
          left: p.left,
          top: p.top,
          animationDelay: p.delay,
          background: p.color === 'primary' ? '#4d44e3' : '#575e78',
        }
        if (p.round) {
          base.width = '6px'
          base.height = '6px'
          base.borderRadius = '9999px'
        }
        return (
          <span
            key={i}
            className={`confetti${p.round ? ' rounded-full' : ''}`}
            style={base}
          />
        )
      })}
    </div>
  )
}
