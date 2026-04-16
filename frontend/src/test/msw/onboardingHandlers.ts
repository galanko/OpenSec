/**
 * MSW handlers for the onboarding endpoints. Used by both the Vitest node
 * server (component tests) and the browser service worker (dev-mode UI).
 *
 * The `verified` payload is a display-only extension — the real OpenAPI
 * response is just `{ assessment_id, repo_url }`. See `api/onboarding.ts`.
 */
import { http, HttpResponse } from 'msw'

export interface StubbedRepoRequest {
  repo_url: string
  github_token: string
}

function deriveRepoName(url: string): string {
  try {
    const u = new URL(url)
    const parts = u.pathname.replace(/^\//, '').replace(/\.git$/, '').split('/')
    return parts.slice(-2).join('/') || url
  } catch {
    return url
  }
}

export const onboardingHandlers = [
  http.post('/api/onboarding/repo', async ({ request }) => {
    const body = (await request.json()) as StubbedRepoRequest

    if (!body?.repo_url || !body?.github_token) {
      return HttpResponse.json(
        { detail: 'repo_url and github_token are required' },
        { status: 422 },
      )
    }

    // Deterministic error path: any PAT that encodes "no-repo-scope"
    // (case-insensitive substring) returns a 403 that the UI renders as
    // frame 1.2 (missing `repo` scope).
    if (/no-?repo-?scope/i.test(body.github_token)) {
      return HttpResponse.json(
        {
          detail:
            "Your token is missing the 'repo' scope. Regenerate the token with the 'repo' box checked and try again.",
          code: 'missing_repo_scope',
        },
        { status: 403 },
      )
    }

    const repoName = deriveRepoName(body.repo_url)
    return HttpResponse.json({
      assessment_id: 'asmt_msw_001',
      repo_url: body.repo_url,
      // Display-only stub fields consumed by ConnectionResultCard.
      verified: {
        repo_name: repoName,
        visibility: 'public',
        default_branch: 'main',
        permissions: ['repo', 'read:user'],
      },
    })
  }),

  http.post('/api/onboarding/complete', async ({ request }) => {
    const body = (await request.json()) as { assessment_id: string }
    if (!body?.assessment_id) {
      return HttpResponse.json(
        { detail: 'assessment_id is required' },
        { status: 422 },
      )
    }
    return HttpResponse.json({ onboarding_completed: true })
  }),
]
