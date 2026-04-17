"""FakeAssessmentEngine — test double standing in for Session A's real engine.

Conforms to ``AssessmentEngineProtocol``. Returns a canned ``AssessmentResult`` so
Session B's route tests can exercise the full happy path before Session A's engine
ships. Session G replaces this with the real engine through the same DI seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opensec.models import AssessmentResult, CriteriaSnapshot, Grade

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class FakeAssessmentEngine:
    """In-memory stub that mirrors Session A's interface."""

    def __init__(
        self,
        *,
        grade: Grade = "B",
        criteria: CriteriaSnapshot | None = None,
        posture_checks: list[dict] | None = None,
        findings: list[dict] | None = None,
        raise_on_run: Exception | None = None,
    ) -> None:
        self.grade = grade
        self.criteria = criteria or CriteriaSnapshot(
            no_critical_vulns=True,
            posture_checks_passing=3,
            posture_checks_total=5,
            security_md_present=True,
            dependabot_present=False,
        )
        self.posture_checks = posture_checks if posture_checks is not None else [
            {"check_name": "branch_protection", "status": "pass"},
            {"check_name": "signed_commits", "status": "advisory"},
        ]
        self.findings = findings or []
        self.raise_on_run = raise_on_run
        self.call_count = 0

    async def run_assessment(
        self,
        repo_url: str,
        *,
        assessment_id: str,
        on_step: Callable[[str], Awaitable[None]] | None = None,
    ) -> AssessmentResult:
        self.call_count += 1
        if on_step is not None:
            # Mirror the real engine's phase sequence so route tests that
            # poll ``GET /assessment/status`` get meaningful step values.
            for step in (
                "parsing_lockfiles",
                "looking_up_cves",
                "checking_posture",
                "grading",
            ):
                await on_step(step)
        if self.raise_on_run is not None:
            raise self.raise_on_run
        return AssessmentResult(
            assessment_id=assessment_id,
            repo_url=repo_url,
            grade=self.grade,
            criteria_snapshot=self.criteria,
            findings=self.findings,
            posture_checks=self.posture_checks,
        )
