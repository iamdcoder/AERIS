from types import SimpleNamespace

import pytest

from copilot.agent import (
    AgentOrchestrator,
)
from copilot.agent.state import (
    AgentStage,
    RunStatus,
)
from copilot.llm import (
    GeminiClient,
)
from copilot.mock_engine import MockEngineClient
from copilot.tools import (
    build_default_registry as _build_default_registry,
)


def build_default_registry():
    return _build_default_registry(MockEngineClient())


def _require_genai_sdk():
    pytest.importorskip("google.genai", reason="Gemini tool-loop tests require google-genai")


class FakeGeminiModels:
    def __init__(self):
        self.calls = 0

    def generate_content(
        self,
        *,
        model,
        contents,
        config,
    ):
        self.calls += 1

        if self.calls == 1:
            function_call = (
                SimpleNamespace(
                    id="call-weather",
                    name="get_weather_state",
                    args={},
                )
            )

            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(
                            parts=[
                                SimpleNamespace(
                                    function_call=(
                                        function_call
                                    ),
                                    text=None,
                                )
                            ]
                        )
                    )
                ],
                text=None,
            )

        text = (
            "Investigation complete. "
            "Severe convective weather remains "
            "a significant operational factor."
        )

        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=SimpleNamespace(
                        parts=[
                            SimpleNamespace(
                                function_call=None,
                                text=text,
                            )
                        ]
                    )
                )
            ],
            text=text,
        )


def build_fake_investigator():
    from copilot.agent.gemini_runner import (
        GeminiInvestigator,
    )

    fake_models = (
        FakeGeminiModels()
    )

    fake_client = SimpleNamespace(
        models=fake_models
    )

    gemini = GeminiClient(
        client=fake_client,
        model="test-model",
    )

    return GeminiInvestigator(
        registry=(
            build_default_registry()
        ),
        gemini_client=gemini,
    )


def test_hybrid_preview_can_finish_with_gemini_investigation():
    investigator = (
        build_fake_investigator()
    )

    orchestrator = (
        AgentOrchestrator(
            registry=(
                build_default_registry()
            ),
            gemini_investigator=(
                investigator
            ),
        )
    )

    state = (
        orchestrator.run_hybrid_preview()
    )

    assert (
        state.stage
        == AgentStage.HUMAN_APPROVAL
    )

    assert (
        state.status
        == RunStatus.WAITING_HUMAN
    )

    assert (
        state.recommendation
        is not None
    )

    assert (
        state.recommendation
        .candidate_id
        == "ALT-D"
    )


def test_hybrid_investigation_writes_memory():
    _require_genai_sdk()
    investigator = (
        build_fake_investigator()
    )

    result = (
        investigator.investigate()
    )

    assert (
        result.status
        == "COMPLETED"
    )

    assert (
        result.working_memory
    )

    categories = {
        item["category"]
        for item
        in result.working_memory
    }

    assert (
        "TOOL_RESULT"
        in categories
    )


def test_hybrid_investigation_returns_structured_results():
    _require_genai_sdk()
    investigator = (
        build_fake_investigator()
    )

    result = (
        investigator.investigate()
    )

    assert (
        result.investigation_plan
        is not None
    )

    assert (
        result.investigation_results
    )

    assert (
        result.evidence
    )

    assert (
        result.tool_calls
    )


def test_hybrid_fallback_preserves_end_to_end_pipeline():
    class BrokenInvestigator:
        def investigate(
            self,
            **kwargs,
        ):
            from copilot.agent.gemini_runner import (
                InvestigationRunResult,
            )
            from copilot.llm import (
                GeminiRunResult,
            )
            from copilot.agent.investigation_quality import (
                InvestigationQuality,
            )

            return InvestigationRunResult(
                execution=(
                    GeminiRunResult(
                        status="FAILED",
                        errors=[
                            "simulated Gemini outage"
                        ],
                    )
                ),
                quality=(
                    InvestigationQuality(
                        sufficient=False,
                        score=0.0,
                        missing_checks=[
                            "get_weather_state"
                        ],
                        reasons=[
                            "Gemini unavailable"
                        ],
                    )
                ),
            )

    orchestrator = (
        AgentOrchestrator(
            registry=(
                build_default_registry()
            ),
            gemini_investigator=(
                BrokenInvestigator()
            ),
        )
    )

    state = (
        orchestrator.run_hybrid_preview()
    )

    assert (
        state.stage
        == AgentStage.HUMAN_APPROVAL
    )

    assert (
        state.status
        == RunStatus.WAITING_HUMAN
    )

    assert (
        state.recommendation
        is not None
    )

    assert (
        state.recommendation.candidate_id
        == "ALT-D"
    )

    fallback_events = [
        event
        for event
        in state.events
        if event.event_type
        == "AGENT_FALLBACK"
    ]

    assert fallback_events


def test_hybrid_run_resets_evidence_between_runs():
    investigator = (
        build_fake_investigator()
    )

    orchestrator = (
        AgentOrchestrator(
            registry=(
                build_default_registry()
            ),
            gemini_investigator=(
                investigator
            ),
        )
    )

    first = (
        orchestrator.run_hybrid_preview()
    )

    first_ids = [
        item[
            "evidence_id"
        ]
        for item
        in first.evidence
    ]

    second = (
        orchestrator.run_hybrid_preview()
    )

    second_ids = [
        item[
            "evidence_id"
        ]
        for item
        in second.evidence
    ]

    assert first_ids
    assert second_ids

    assert (
        second_ids[0]
        == "E001"
    )