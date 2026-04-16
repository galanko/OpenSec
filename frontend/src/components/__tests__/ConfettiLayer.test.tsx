import { render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ConfettiLayer from '../completion/ConfettiLayer'

function setPrefersReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query.includes('prefers-reduced-motion: reduce') ? matches : false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('ConfettiLayer', () => {
  afterEach(() => {
    // Reset matchMedia between tests so state doesn't leak.
    vi.restoreAllMocks()
  })

  it('renders 12 confetti particles when motion is allowed', () => {
    setPrefersReducedMotion(false)
    const { container } = render(<ConfettiLayer />)
    const particles = container.querySelectorAll('.confetti')
    expect(particles.length).toBe(12)
  })

  it('renders nothing when the user has requested reduced motion', () => {
    setPrefersReducedMotion(true)
    const { container } = render(<ConfettiLayer />)
    expect(container.firstChild).toBeNull()
  })

  it('is marked aria-hidden — confetti is decoration only', () => {
    setPrefersReducedMotion(false)
    const { container } = render(<ConfettiLayer />)
    const wrapper = container.firstElementChild as HTMLElement
    expect(wrapper.getAttribute('aria-hidden')).toBe('true')
  })
})
