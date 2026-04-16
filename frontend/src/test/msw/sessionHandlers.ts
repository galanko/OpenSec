/**
 * Test-only MSW handlers for routes served by the real backend in production
 * but that component tests still want to stub deterministically. Loaded by
 * vitest only (``src/test-setup.ts`` installs them in ``beforeEach``); never
 * shipped to the dev service worker.
 *
 * Tests can override per-case via ``server.use(...)`` or ``setDashboardFixture``;
 * ``afterEach(() => server.resetHandlers())`` cleans up between tests.
 */
import { http, HttpResponse } from 'msw'
import {
  assessmentStatusSteps,
  getDashboardFixture,
  type DashboardFixtureName,
} from '../../mocks/fixtures/dashboard'

let activeFixture: DashboardFixtureName = 'grade-C-with-issues'

export function setDashboardFixture(name: DashboardFixtureName): void {
  activeFixture = name
}

export function getActiveDashboardFixture(): DashboardFixtureName {
  return activeFixture
}

let statusPollIndex = 0

export function resetStatusPoll(): void {
  statusPollIndex = 0
}

export type ShareAction = 'download' | 'copy_text' | 'copy_markdown'

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

export const sessionHandlers = [
  // Default the flag ON so gated routes render normally in component tests.
  // FeatureFlagGate tests override this per-case via ``server.use(...)`` to
  // cover the redirect paths.
  http.get('/api/config/feature-flags', () =>
    HttpResponse.json({
      v1_1_from_zero_to_secure_enabled: true,
      onboarding_completed: true,
      has_any_assessment: true,
    }),
  ),

  http.post('/api/onboarding/repo', async ({ request }) => {
    const body = (await request.json()) as StubbedRepoRequest

    if (!body?.repo_url || !body?.github_token) {
      return HttpResponse.json(
        { detail: 'repo_url and github_token are required' },
        { status: 422 },
      )
    }

    if (body.github_token === 'no-repo-scope') {
      return HttpResponse.json(
        {
          detail:
            "Your token is missing the 'repo' scope. Regenerate the token with the 'repo' box checked and try again.",
          code: 'missing_repo_scope',
        },
        { status: 403 },
      )
    }

    return HttpResponse.json({
      assessment_id: 'asmt_msw_001',
      repo_url: body.repo_url,
      verified: {
        repo_name: deriveRepoName(body.repo_url),
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

  http.get('/api/dashboard', () =>
    HttpResponse.json(getDashboardFixture(activeFixture)),
  ),

  http.get('/api/assessment/status/:id', () => {
    const step = assessmentStatusSteps[
      Math.min(statusPollIndex, assessmentStatusSteps.length - 1)
    ]
    statusPollIndex += 1
    return HttpResponse.json(step)
  }),

  http.post('/api/posture/fix/:checkName', ({ params }) => {
    const checkName = params.checkName as 'security_md' | 'dependabot_config'
    return HttpResponse.json({
      check_name: checkName,
      workspace_id: `ws_${checkName}_stub`,
    })
  }),

  http.get('/api/settings/providers', () =>
    HttpResponse.json([
      {
        id: 'openai',
        name: 'OpenAI',
        env: ['OPENAI_API_KEY'],
        models: {
          'gpt-4o': { id: 'gpt-4o', name: 'GPT-4o' },
          'gpt-4o-mini': { id: 'gpt-4o-mini', name: 'GPT-4o mini' },
        },
      },
      {
        id: 'anthropic',
        name: 'Anthropic',
        env: ['ANTHROPIC_API_KEY'],
        models: {
          'claude-3-5-sonnet': {
            id: 'claude-3-5-sonnet',
            name: 'Claude 3.5 Sonnet',
          },
        },
      },
      {
        id: 'google',
        name: 'Google',
        env: ['GOOGLE_API_KEY'],
        models: {
          'gemini-1.5-pro': { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro' },
        },
      },
    ]),
  ),

  http.put('/api/settings/model', async ({ request }) => {
    const body = (await request.json()) as { model_full_id: string }
    const [provider, ...rest] = body.model_full_id.split('/')
    return HttpResponse.json({
      model_full_id: body.model_full_id,
      provider,
      model_id: rest.join('/'),
    })
  }),

  http.post('/api/completion/:id/share-action', async ({ params, request }) => {
    const body = (await request.json()) as { action: ShareAction }
    return HttpResponse.json(
      {
        completion_id: String(params.id),
        share_actions_used: [body.action],
      },
      { status: 200 },
    )
  }),
]
