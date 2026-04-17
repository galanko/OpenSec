# Security Policy

OpenSec is a self-hosted cybersecurity remediation copilot. We take the security of both OpenSec itself and of the projects it operates on seriously.

## Supported versions

OpenSec is pre-1.0. Only the latest `main` tip is actively supported. Security fixes are applied directly to `main` and released in the next tagged version.

| Version | Supported |
|---------|-----------|
| `main` (latest)  | Yes |
| Older revisions  | No — please upgrade |

## Reporting a vulnerability

**Please do not file a public GitHub issue for security reports.**

Email [galank@gmail.com](mailto:galank@gmail.com) with:

- A brief description of the issue and its impact.
- Steps to reproduce (or a minimal proof of concept).
- The OpenSec commit SHA or release tag you tested against.
- Optionally, a suggested fix.

We aim to:

- Acknowledge your report within **3 business days**.
- Provide an initial triage + severity assessment within **7 business days**.
- Ship a fix (or document a mitigation) before disclosing the issue publicly.

If the bug qualifies for a CVE we will coordinate the disclosure with you.

## Scope

In scope:

- The Python backend (`backend/opensec`)
- The React frontend (`frontend/`)
- The Docker packaging (`docker/`)
- Default adapter and agent templates (`backend/opensec/agents/`, `backend/opensec/integrations/`)

Out of scope:

- Findings about third-party dependencies that do not require an OpenSec-side change (file them upstream first).
- Denial-of-service that requires the attacker to already hold administrator access to the host OpenSec runs on.

## Safe-harbor

We will not pursue legal action against good-faith researchers who follow this policy, stop at the proof-of-concept stage, and avoid accessing data that is not their own.

Thanks for helping keep OpenSec — and the projects we guard — safe.
