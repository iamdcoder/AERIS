from types import SimpleNamespace

from copilot.llm import (
    GeminiClient,
)
from copilot.tools import (
    build_default_registry,
)


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
            function_call = SimpleNamespace(
                id="call-001",
                name="get_sector_state",
                args={
                    "sector_id": "S5"
                },
            )

            function_part = SimpleNamespace(
                function_call=function_call,
                text=None,
            )

            content = SimpleNamespace(
                parts=[
                    function_part
                ]
            )

            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=content
                    )
                ],
                text=None,
            )

        text_part = SimpleNamespace(
            function_call=None,
            text=(
                "Investigation complete. "
                "Sector S5 is stressed and "
                "requires network-aware evaluation."
            ),
        )

        content = SimpleNamespace(
            parts=[
                text_part
            ]
        )

        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=content
                )
            ],
            text=(
                "Investigation complete. "
                "Sector S5 is stressed and "
                "requires network-aware evaluation."
            ),
        )


class FakeModelsWithUnknownTool:
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

        function_call = SimpleNamespace(
            id="call-unknown",
            name="invented_tool",
            args={},
        )

        function_part = SimpleNamespace(
            function_call=function_call,
            text=None,
        )

        content = SimpleNamespace(
            parts=[
                function_part
            ]
        )

        return SimpleNamespace(
            candidates=[
                SimpleNamespace(
                    content=content
                )
            ],
            text=None,
        )


def test_gemini_client_executes_model_requested_tool():
    fake_models = FakeModels()

    fake_client = SimpleNamespace(
        models=fake_models
    )

    registry = (
        build_default_registry()
    )

    client = GeminiClient(
        client=fake_client,
        model="test-model",
    )

    result = client.run(
        prompt=(
            "Investigate F102."
        ),
        registry=registry,
        system_instruction=(
            "Use tools to investigate."
        ),
    )

    assert (
        result.status
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

    assert (
        "Sector S5"
        in result.final_text
    )


def test_unknown_model_requested_tool_is_contained():
    fake_models = (
        FakeModelsWithUnknownTool()
    )

    fake_client = SimpleNamespace(
        models=fake_models
    )

    registry = (
        build_default_registry()
    )

    client = GeminiClient(
        client=fake_client,
        model="test-model",
        max_rounds=1,
    )

    result = client.run(
        prompt="Investigate.",
        registry=registry,
        system_instruction=(
            "Use tools to investigate."
        ),
    )

    assert (
        result.status
        == "DEGRADED"
    )

    assert (
        len(
            result.tool_calls
        )
        == 1
    )

    assert (
        result.tool_calls[0].ok
        is False
    )

    assert (
        result.tool_calls[0].error_code
        == "TOOL_NOT_FOUND"
    )