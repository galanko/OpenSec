/**
 * Thin fetch wrapper for the onboarding endpoints. Mirrors the OpenAPI
 * contract in `src/api/types.ts`:
 *   POST /api/onboarding/repo     — verify repo + PAT
 *   POST /api/onboarding/complete — mark onboarding complete
 */

const BASE = ''

export interface OnboardingRepoRequest {
  repo_url: string
  github_token: string
}

/** Display-only metadata for the verified-connection card (UX frame 1.3).
 *  Today this is populated by MSW stubs; when the backend grows these
 *  fields it can be returned alongside `assessment_id`. If the backend
 *  declines, this shape can be derived locally from `repo_url`. */
export interface VerifiedRepoSummary {
  repo_name: string
  visibility: 'public' | 'private' | string
  default_branch: string
  permissions: string[]
}

export interface OnboardingRepoResponse {
  assessment_id: string
  repo_url: string
  verified?: VerifiedRepoSummary
}

export interface OnboardingCompleteRequest {
  assessment_id: string
}

export interface OnboardingCompleteResponse {
  onboarding_completed: boolean
}

export class OnboardingApiError extends Error {
  status: number
  code?: string
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'OnboardingApiError'
    this.status = status
    this.code = code
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    let code: string | undefined
    try {
      const data = await resp.json()
      if (typeof data?.detail === 'string') detail = data.detail
      if (typeof data?.code === 'string') code = data.code
    } catch {
      /* non-JSON error body */
    }
    throw new OnboardingApiError(detail, resp.status, code)
  }
  return resp.json() as Promise<T>
}

export const onboardingApi = {
  connectRepo: (req: OnboardingRepoRequest) =>
    postJson<OnboardingRepoResponse>('/api/onboarding/repo', req),

  complete: (req: OnboardingCompleteRequest) =>
    postJson<OnboardingCompleteResponse>('/api/onboarding/complete', req),
}
