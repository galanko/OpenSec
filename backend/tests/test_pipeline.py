"""Tests for the pipeline orchestrator."""

from __future__ import annotations

from opensec.agents.pipeline import (
    MAX_RETRY_ITERATIONS,
    PIPELINE_ORDER,
    suggest_next,
)


class TestSuggestNext:
    def test_empty_context_suggests_enricher(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": None,
            "ownership": None,
            "exposure": None,
            "plan": None,
            "validation": None,
        }
        result = suggest_next(snapshot)
        assert result is not None
        assert result.agent_type == "finding_enricher"
        assert result.priority == "recommended"

    def test_enrichment_done_suggests_owner(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": None,
            "exposure": None,
            "plan": None,
            "validation": None,
        }
        result = suggest_next(snapshot)
        assert result is not None
        assert result.agent_type == "owner_resolver"

    def test_through_exposure_suggests_planner(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": None,
            "validation": None,
        }
        result = suggest_next(snapshot)
        assert result is not None
        assert result.agent_type == "remediation_planner"

    def test_plan_done_suggests_validation(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["Step 1"]},
            "validation": None,
        }
        result = suggest_next(snapshot)
        assert result is not None
        assert result.agent_type == "validation_checker"

    def test_all_complete_returns_none(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["Step 1"]},
            "validation": {"verdict": "fixed", "recommendation": "close"},
        }
        result = suggest_next(snapshot)
        assert result is None

    def test_validation_not_fixed_retries_planner(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["Step 1"]},
            "validation": {"verdict": "not_fixed", "recommendation": "replan"},
        }
        history = [
            {"agent_type": "remediation_planner", "status": "completed"},
        ]
        result = suggest_next(snapshot, history)
        assert result is not None
        assert result.agent_type == "remediation_planner"
        assert result.priority == "required"

    def test_validation_partially_fixed_retries(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["Step 1"]},
            "validation": {"verdict": "partially_fixed", "recommendation": "replan"},
        }
        result = suggest_next(snapshot, [])
        assert result is not None
        assert result.agent_type == "remediation_planner"

    def test_retry_limit_reached_returns_none(self):
        snapshot = {
            "finding": {"id": "f-1"},
            "enrichment": {"normalized_title": "Test"},
            "ownership": {"recommended_owner": "Team A"},
            "exposure": {"recommended_urgency": "high"},
            "plan": {"plan_steps": ["Step 1"]},
            "validation": {"verdict": "not_fixed", "recommendation": "replan"},
        }
        # MAX_RETRY_ITERATIONS completed planner runs
        history = [
            {"agent_type": "remediation_planner", "status": "completed"}
            for _ in range(MAX_RETRY_ITERATIONS)
        ]
        result = suggest_next(snapshot, history)
        assert result is None

    def test_pipeline_order_is_correct(self):
        assert PIPELINE_ORDER == [
            "finding_enricher",
            "owner_resolver",
            "exposure_analyzer",
            "remediation_planner",
            "validation_checker",
        ]
