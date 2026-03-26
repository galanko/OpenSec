# ADR-0011: Stitch-Generated Design System ("Serene Sentinel")

**Date:** 2026-03-26
**Status:** Accepted
**Supersedes:** Parts of ADR-0003 (shadcn/ui component library choice)

## Context

Phase 2 requires a coherent design system for the five-page app shell. ADR-0003 specified shadcn/ui (Radix UI + Tailwind) as the component library. During Phase 2 planning, we used Google Stitch AI to generate a complete design system and screen mockups for all five pages, producing a distinctive "Editorial Assurance" aesthetic that diverges from generic component library patterns.

The Stitch output includes:
- A named design system ("Ethos Security" / "Serene Sentinel") with 65+ color tokens
- Full HTML mockups for Queue, Workspace, History, Integrations, and Settings
- Typography pairing (Manrope headlines + Inter body)
- Material Symbols Outlined icon set
- Detailed design rules (No-Line Rule, Tonal Layering, Ghost Borders)

## Decision

Use the Stitch-generated design system as the canonical UI reference instead of shadcn/ui. Build custom Tailwind components that match the Stitch mockups exactly.

**What changes from ADR-0003:**
- **Icons:** Material Symbols Outlined (Google Fonts CDN) instead of lucide-react
- **Components:** Custom Tailwind components instead of shadcn/ui (Radix UI)
- **Color mode:** Light mode default instead of dark mode
- **Color palette:** 65+ Stitch tokens instead of HSL CSS variables

**What stays the same from ADR-0003:**
- React 19 + TypeScript + Vite
- Tailwind CSS (v3 for Stitch config compatibility)
- Component-based architecture
- No Next.js / SSR

## Consequences

**Positive:**
- Unique, distinctive design that avoids generic "AI slop" aesthetics
- Complete visual reference for all pages (HTML + screenshots)
- Rich color token system designed specifically for cybersecurity context
- Editorial, calm aesthetic differentiates from typical security dashboards

**Negative:**
- No pre-built accessible components from Radix UI — must handle a11y manually where needed
- Material Symbols requires CDN or self-hosted font (adds external dependency)
- Tailwind v3 instead of v4 (pinned to match Stitch config format)

## References

- Stitch project ID: `12683083125265338263`
- Design system asset: `assets/4b12e656418a48a3ac0b581fa08bf723`
- Mockup files: `frontend/mockups/html/*.html` and `frontend/mockups/screenshots/*.png`
- Color tokens source of truth: `frontend/tailwind.config.ts`
