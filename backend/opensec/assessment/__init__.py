"""Deterministic assessment engine (IMPL-0002 Milestone B, ADR-0025).

Given a local repo path, produces an `AssessmentResult` with vulnerability
findings (from OSV/GHSA lookups over parsed lockfiles) and repo posture
checks. No LLM, no DB writes — Session B owns persistence.
"""

from __future__ import annotations

from opensec.assessment.engine import (
    derive_grade,
    run_assessment,
    run_assessment_on_path,
)

__all__ = ["derive_grade", "run_assessment", "run_assessment_on_path"]
