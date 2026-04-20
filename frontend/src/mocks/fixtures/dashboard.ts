/**
 * Dashboard API fixtures for MSW handlers and tests.
 *
 * Three seeded states per EXEC-0002 Session E contract:
 *   - assessment-running        — scan in-flight, no grade yet
 *   - grade-C-with-issues       — 3 of 5 criteria met, vulns + failing posture
 *   - grade-A-completion-holding — 5 of 5 criteria met, completion active
 */

import type { components } from '@/api/types'

export type DashboardPayload = components['schemas']['DashboardPayload']
export type Assessment = components['schemas']['Assessment']
export type AssessmentStatusResponse =
  components['schemas']['AssessmentStatusResponse']
export type Finding = components['schemas']['Finding']
export type PostureFixResponse = components['schemas']['PostureFixResponse']
export type CriteriaSnapshot = components['schemas']['CriteriaSnapshot']

// ---------------------------------------------------------------------------
// Common timestamps
// ---------------------------------------------------------------------------

const NOW = '2026-04-16T09:00:00Z'
const EARLIER = '2026-04-16T08:30:00Z'

// ---------------------------------------------------------------------------
// Assessment objects (match frozen schema — status: pending|running|complete|failed)
// ---------------------------------------------------------------------------

const runningAssessment: Assessment = {
  id: 'asmt_running_001',
  repo_url: 'https://github.com/acme/fast-markdown',
  status: 'running',
  grade: null,
  started_at: EARLIER,
  completed_at: null,
  criteria_snapshot: null,
}

// The 7 posture checks here are the "other" governance checks (branch
// protection, signed commits, code scanning, etc.) — disjoint from
// security_md_present + dependabot_present, which are separate completion
// criteria. This disjointness is what makes "3 of 5 criteria met" + "7 of 7
// posture checks passing" + "2 failing items to fix" internally consistent.
const completedAssessmentC: Assessment = {
  id: 'asmt_c_001',
  repo_url: 'https://github.com/acme/fast-markdown',
  status: 'complete',
  grade: 'C',
  started_at: EARLIER,
  completed_at: NOW,
  criteria_snapshot: {
    security_md_present: false,
    dependabot_present: false,
    no_critical_vulns: true,
    posture_checks_passing: 7,
    posture_checks_total: 7,
  },
}

const completedAssessmentA: Assessment = {
  id: 'asmt_a_001',
  repo_url: 'https://github.com/acme/fast-markdown',
  status: 'complete',
  grade: 'A',
  started_at: EARLIER,
  completed_at: NOW,
  criteria_snapshot: {
    security_md_present: true,
    dependabot_present: true,
    no_critical_vulns: true,
    posture_checks_passing: 7,
    posture_checks_total: 7,
  },
}

// ---------------------------------------------------------------------------
// Payloads
// ---------------------------------------------------------------------------

export const assessmentRunningPayload: DashboardPayload = {
  assessment: runningAssessment,
  completion_id: null,
  criteria: {
    security_md_present: false,
    dependabot_present: false,
    no_critical_vulns: false,
    posture_checks_passing: 0,
    posture_checks_total: 0,
  },
  findings_count_by_priority: {},
  grade: null,
  posture_checks: [],
  posture_pass_count: 0,
  posture_total_count: 0,
}

export const gradeCWithIssuesPayload: DashboardPayload = {
  assessment: completedAssessmentC,
  completion_id: null,
  criteria: {
    security_md_present: false,
    dependabot_present: false,
    no_critical_vulns: true,
    posture_checks_passing: 7,
    posture_checks_total: 7,
  },
  findings_count_by_priority: {
    critical: 1,
    high: 2,
    medium: 3,
    low: 1,
  },
  grade: 'C',
  posture_checks: [],
  posture_pass_count: 7,
  posture_total_count: 7,
}

export const gradeACompletionHoldingPayload: DashboardPayload = {
  assessment: completedAssessmentA,
  completion_id: 'cmp_001',
  criteria: {
    security_md_present: true,
    dependabot_present: true,
    no_critical_vulns: true,
    posture_checks_passing: 7,
    posture_checks_total: 7,
  },
  findings_count_by_priority: {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  },
  grade: 'A',
  posture_checks: [],
  posture_pass_count: 7,
  posture_total_count: 7,
}

// ---------------------------------------------------------------------------
// Findings (plain-language, for FindingRow + FindingDetailPage)
// ---------------------------------------------------------------------------

export const sampleFindings: Finding[] = [
  {
    id: 'fnd_001',
    source_type: 'osv',
    source_id: 'CVE-2024-4067',
    title: 'A pattern-matching library your project uses has a known flaw',
    description:
      'The braces npm package can be tricked into infinite loops when handed malicious input.',
    plain_description:
      'The braces npm package can be tricked into infinite loops when handed malicious input. The fix is a one-line bump: braces 3.0.2 → 3.0.3.',
    raw_severity: 'critical',
    normalized_priority: 'critical',
    asset_id: 'pkg_braces',
    asset_label: 'braces@3.0.2',
    status: 'new',
    likely_owner: null,
    why_this_matters: null,
    raw_payload: {
      cve: 'CVE-2024-4067',
      cvss_score: 7.5,
      attack_vector: 'regex denial-of-service',
    },
    created_at: EARLIER,
    updated_at: NOW,
  },
  {
    id: 'fnd_002',
    source_type: 'osv',
    source_id: 'CVE-2023-45857',
    title: 'Your HTTP client leaks session tokens through a secondary request',
    description:
      'axios versions before 1.6.0 forward authorization headers on cross-origin redirects.',
    plain_description:
      'axios versions before 1.6.0 forward authorization headers on cross-origin redirects. Bump to 1.6.0 or later.',
    raw_severity: 'high',
    normalized_priority: 'high',
    asset_id: 'pkg_axios',
    asset_label: 'axios@1.5.1',
    status: 'new',
    likely_owner: null,
    why_this_matters: null,
    raw_payload: {
      cve: 'CVE-2023-45857',
      cvss_score: 6.5,
      attack_vector: 'credential leak via redirect',
    },
    created_at: EARLIER,
    updated_at: NOW,
  },
]

// ---------------------------------------------------------------------------
// Assessment status progression (for poll/SSE — Session B upgrades to SSE later)
// ---------------------------------------------------------------------------

export const assessmentStatusSteps: AssessmentStatusResponse[] = [
  {
    assessment_id: runningAssessment.id,
    status: 'running',
    progress_pct: 10,
    step: 'cloning',
  },
  {
    assessment_id: runningAssessment.id,
    status: 'running',
    progress_pct: 25,
    step: 'parsing_lockfiles',
  },
  {
    assessment_id: runningAssessment.id,
    status: 'running',
    progress_pct: 50,
    step: 'looking_up_cves',
  },
  {
    assessment_id: runningAssessment.id,
    status: 'running',
    progress_pct: 75,
    step: 'checking_posture',
  },
  {
    assessment_id: runningAssessment.id,
    status: 'running',
    progress_pct: 90,
    step: 'grading',
  },
  {
    assessment_id: runningAssessment.id,
    status: 'complete',
    progress_pct: 100,
    step: null,
  },
]

// ---------------------------------------------------------------------------
// Named selector used by tests + handlers to choose active fixture
// ---------------------------------------------------------------------------

export type DashboardFixtureName =
  | 'assessment-running'
  | 'grade-C-with-issues'
  | 'grade-A-completion-holding'

export function getDashboardFixture(
  name: DashboardFixtureName,
): DashboardPayload {
  switch (name) {
    case 'assessment-running':
      return assessmentRunningPayload
    case 'grade-C-with-issues':
      return gradeCWithIssuesPayload
    case 'grade-A-completion-holding':
      return gradeACompletionHoldingPayload
  }
}
