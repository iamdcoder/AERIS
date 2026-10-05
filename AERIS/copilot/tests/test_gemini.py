from types import SimpleNamespace

import pytest

from copilot.agent.gemini_runner import (
    GeminiInvestigator,
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


class FakeModels:
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
                    id="call-001",
                    name="get_sector_state",
                    args={
                        "sector_id": "S5"
                    },
                )
            )

            function_part = (
                SimpleNamespace(
                    function_call=function_call,
                    text=None,
                )
            )

            content = (
                SimpleNamespace(
                    parts=[
                        function_part
                    ]
                )
            )

            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=content
                    )
                ],
                text=None,
            )

        text_part = (
            SimpleNamespace(
                function_call=None,
                text=(
                    "Investigation complete. "
                    "Sector S5 is stressed."
                ),
            )
        )

        content = (
            SimpleNamespace(
                parts=[
                    text_part
                ]
            )
        )

        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=content
                )
            ],
            text=(
                "Investigation complete. "
                "Sector S5 is stressed."
            ),
        )


class FakeModelsWithBlockedTool:
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
                    id="call-blocked",
                    name="generate_alternatives",
                    args={
                        "flight_id": "F102"
                    },
                )
            )

            function_part = (
                SimpleNamespace(
                    function_call=function_call,
                    text=None,
                )
            )

            content = (
                SimpleNamespace(
                    parts=[
                        function_part
                    ]
                )
            )

            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=content
                    )
                ],
                text=None,
            )

        text_part = (
            SimpleNamespace(
                function_call=None,
                text=(
                    "The requested planning tool "
                    "was unavailable during investigation."
                ),
            )
        )

        content = (
            SimpleNamespace(
                parts=[
                    text_part
                ]
            )
        )

        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=content
                )
            ],
            text=(
                "The requested planning tool "
                "was unavailable during investigation."
            ),
        )


def _build_fake_client(
    fake_models,
):
    return SimpleNamespace(
        models=fake_models
    )


def test_gemini_client_executes_allowed_tool():
    _require_genai_sdk()

    fake_models = FakeModels()

    fake_client = _build_fake_client(
        fake_models
    )

    registry = (
        build_default_registry()
    )

    client = GeminiClient(
        client=fake_client,
        model="test-model",
    )

    investigator = GeminiInvestigator(
        registry=registry,
        gemini_client=client,
    )

    result = (
        investigator.investigate()
    )

    assert (
        result.execution.status
        == "COMPLETED"
    )
    assert (
        result.rounds
        == 2
    )

    assert len(
        result.tool_calls
    ) == 1

    assert (
        result.tool_calls[0].name
        == "get_sector_state"
    )

    assert (
        result.tool_calls[0].ok
        is True
    )


def test_investigator_exposes_only_policy_allowed_tools():
    investigator = GeminiInvestigator(
        registry=build_default_registry(),
        gemini_client=GeminiClient(client=SimpleNamespace(models=object()), model="test-model"),
    )

    names = {
        item["name"]
        for item
        in investigator.tool_definitions()
    }

    assert names == {
        "get_airspace_state",
        "get_disruptions",
        "get_target_flight",
        "get_sector_state",
        "get_airport_state",
        "get_weather_state",
        "get_restrictions",
        "get_network_metrics",
    }


def test_investigator_policy_snapshot_is_explicit():
    investigator = GeminiInvestigator(
        registry=build_default_registry(),
        gemini_client=GeminiClient(client=SimpleNamespace(models=object()), model="test-model"),
    )

    snapshot = (
        investigator.policy_snapshot()
    )

    assert (
        snapshot["stage"]
        == "INVESTIGATION"
    )

    assert (
        snapshot["max_total_calls"]
        == 12
    )

    assert (
        "apply_intervention"
        in snapshot[
            "permanently_blocked_tools"
        ]
    )


def test_blocked_tool_call_is_returned_as_structured_failure():
    _require_genai_sdk()
    fake_models = (
        FakeModelsWithBlockedTool()
    )

    fake_client = _build_fake_client(
        fake_models
    )

    registry = (
        build_default_registry()
    )

    client = GeminiClient(
        client=fake_client,
        model="test-model",
    )

    investigator = GeminiInvestigator(
        registry=registry,
        gemini_client=client,
    )

    result = (
        investigator.investigate()
    )

    assert (
        len(result.tool_calls)
        >= 1
    )

    blocked_call = (
        result.tool_calls[0]
    )

    assert (
        blocked_call.name
        == "generate_alternatives"
    )

    assert (
        blocked_call.ok
        is False
    )

    assert (
        blocked_call.error_code
        == "TOOL_NOT_ALLOWED"
    )


def test_investigation_quality_detects_missing_evidence():
    _require_genai_sdk()
    fake_models = FakeModels()

    fake_client = _build_fake_client(
        fake_models
    )

    registry = (
        build_default_registry()
    )

    client = GeminiClient(
        client=fake_client,
        model="test-model",
    )

    investigator = GeminiInvestigator(
        registry=registry,
        gemini_client=client,
    )

    result = (
        investigator.investigate()
    )

    assert (
        result.quality.sufficient
        is False
    )

    assert (
        result.status
        == "INSUFFICIENT_EVIDENCE"
    )

    assert (
        result.quality.missing_checks
    )