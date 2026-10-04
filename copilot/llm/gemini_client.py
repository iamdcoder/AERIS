import os
from typing import Any

from pydantic import BaseModel, Field

from copilot.tools import (
    ToolRegistry,
)


class GeminiConfigurationError(
    RuntimeError
):
    pass


class GeminiToolCall(BaseModel):
    call_id: str | None = None

    name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )

    ok: bool = True

    result_summary: str | None = None

    error_code: str | None = None


class GeminiRunResult(BaseModel):
    status: str

    final_text: str = ""

    rounds: int = 0

    tool_calls: list[
        GeminiToolCall
    ] = Field(
        default_factory=list
    )

    errors: list[str] = Field(
        default_factory=list
    )


class GeminiClient:
    """
    Controlled Gemini function-calling client.

    Responsibilities:
    - create Gemini requests;
    - expose registered function definitions;
    - receive model-requested tool calls;
    - execute them through ToolRegistry;
    - return tool results to Gemini;
    - enforce tool-call and round budgets.

    It does NOT contain aviation-specific logic.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
        max_rounds: int = 8,
        max_tool_calls: int = 20,
    ) -> None:
        self.model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            )
        )

        self.max_rounds = max(
            1,
            max_rounds,
        )

        self.max_tool_calls = max(
            1,
            max_tool_calls,
        )

        self._client = (
            client
            if client is not None
            else self._create_client(
                api_key
            )
        )

    @staticmethod
    def _create_client(
        api_key: str | None,
    ) -> Any:
        resolved_key = (
            api_key
            or os.getenv(
                "GEMINI_API_KEY"
            )
        )

        if not resolved_key:
            raise GeminiConfigurationError(
                (
                    "GEMINI_API_KEY is not configured. "
                    "Set it in the environment before "
                    "using Gemini."
                )
            )

        try:
            from google import genai
        except ImportError as exc:
            raise GeminiConfigurationError(
                (
                    "The google-genai package is not installed. "
                    "Run: pip install google-genai"
                )
            ) from exc

        return genai.Client(
            api_key=resolved_key
        )

    def _build_tools(
        self,
        registry: ToolRegistry,
    ) -> list[Any]:
        """
        Convert provider-neutral AERIS tool definitions
        into Gemini SDK tool objects.
        """
        try:
            from google.genai import types
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai is not installed."
            ) from exc

        declarations = []

        for definition in (
            registry.function_declarations()
        ):
            declarations.append(
                types.FunctionDeclaration(
                    name=definition[
                        "name"
                    ],
                    description=definition[
                        "description"
                    ],
                    parameters=definition[
                        "parameters"
                    ],
                )
            )

        if not declarations:
            return []

        return [
            types.Tool(
                function_declarations=declarations
            )
        ]

    @staticmethod
    def _extract_content(
        response: Any,
    ) -> Any:
        candidates = getattr(
            response,
            "candidates",
            None,
        )

        if not candidates:
            raise RuntimeError(
                "Gemini returned no candidates."
            )

        content = getattr(
            candidates[0],
            "content",
            None,
        )

        if content is None:
            raise RuntimeError(
                "Gemini returned no response content."
            )

        return content

    @staticmethod
    def _extract_function_calls(
        content: Any,
    ) -> list[Any]:
        parts = getattr(
            content,
            "parts",
            [],
        )

        calls = []

        for part in parts:
            function_call = getattr(
                part,
                "function_call",
                None,
            )

            if function_call is not None:
                calls.append(
                    function_call
                )

        return calls

    @staticmethod
    def _extract_text(
        response: Any,
        content: Any,
    ) -> str:
        response_text = getattr(
            response,
            "text",
            None,
        )

        if response_text:
            return str(
                response_text
            )

        parts = getattr(
            content,
            "parts",
            [],
        )

        text_parts = []

        for part in parts:
            text_value = getattr(
                part,
                "text",
                None,
            )

            if text_value:
                text_parts.append(
                    str(text_value)
                )

        return "\n".join(
            text_parts
        ).strip()

    def run(
        self,
        *,
        prompt: str,
        registry: ToolRegistry,
        system_instruction: str,
    ) -> GeminiRunResult:
        """
        Execute a manual Gemini tool-calling loop.

        Automatic function calling is disabled intentionally.
        AERIS executes every requested function through the
        ToolRegistry so that calls are observable and controlled.
        """

        try:
            from google.genai import types
        except ImportError as exc:
            return GeminiRunResult(
                status="FAILED",
                errors=[
                    (
                        "google-genai is not installed."
                    )
                ],
            )

        tools = self._build_tools(
            registry
        )

        contents: list[Any] = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=prompt
                    )
                ],
            )
        ]

        tool_calls: list[
            GeminiToolCall
        ] = []

        errors: list[str] = []

        total_calls = 0

        try:
            for round_number in range(
                1,
                self.max_rounds + 1,
            ):
                config = (
                    types.GenerateContentConfig(
                        tools=tools,
                        system_instruction=(
                            system_instruction
                        ),
                        automatic_function_calling=(
                            types.AutomaticFunctionCallingConfig(
                                disable=True
                            )
                        ),
                    )
                )

                response = (
                    self._client
                    .models
                    .generate_content(
                        model=self.model,
                        contents=contents,
                        config=config,
                    )
                )

                content = (
                    self._extract_content(
                        response
                    )
                )

                function_calls = (
                    self._extract_function_calls(
                        content
                    )
                )

                if not function_calls:
                    final_text = (
                        self._extract_text(
                            response,
                            content,
                        )
                    )

                    return GeminiRunResult(
                        status="COMPLETED",
                        final_text=final_text,
                        rounds=round_number,
                        tool_calls=tool_calls,
                        errors=errors,
                    )

                # Preserve the model's function-call message
                # before returning function results.
                contents.append(
                    content
                )

                function_response_parts = []

                for function_call in (
                    function_calls
                ):
                    total_calls += 1

                    call_name = str(
                        function_call.name
                    )

                    call_id = getattr(
                        function_call,
                        "id",
                        None,
                    )

                    raw_arguments = getattr(
                        function_call,
                        "args",
                        {},
                    )

                    try:
                        arguments = dict(
                            raw_arguments
                            or {}
                        )
                    except (
                        TypeError,
                        ValueError,
                    ) as exc:
                        arguments = {}

                        tool_call = (
                            GeminiToolCall(
                                call_id=call_id,
                                name=call_name,
                                arguments={},
                                ok=False,
                                error_code=(
                                    "INVALID_TOOL_ARGUMENTS"
                                ),
                                result_summary=(
                                    str(exc)
                                ),
                            )
                        )

                        tool_calls.append(
                            tool_call
                        )

                        error_payload = {
                            "ok": False,
                            "error_code": (
                                "INVALID_TOOL_ARGUMENTS"
                            ),
                            "error_message": (
                                str(exc)
                            ),
                        }

                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=call_name,
                                response=error_payload,
                            )
                        )

                        continue

                    if total_calls > (
                        self.max_tool_calls
                    ):
                        message = (
                            "Gemini exceeded the "
                            "AERIS tool-call budget."
                        )

                        errors.append(
                            message
                        )

                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=call_name,
                                response={
                                    "ok": False,
                                    "error_code": (
                                        "TOOL_CALL_BUDGET_EXCEEDED"
                                    ),
                                    "error_message": message,
                                },
                            )
                        )

                        return GeminiRunResult(
                            status="DEGRADED",
                            final_text="",
                            rounds=round_number,
                            tool_calls=tool_calls,
                            errors=errors,
                        )

                    result = (
                        registry.invoke(
                            call_name,
                            arguments,
                        )
                    )

                    tool_call = (
                        GeminiToolCall(
                            call_id=call_id,
                            name=call_name,
                            arguments=arguments,
                            ok=result.ok,
                            result_summary=(
                                result.summary
                            ),
                            error_code=(
                                result.error_code
                            ),
                        )
                    )

                    tool_calls.append(
                        tool_call
                    )

                    function_response_parts.append(
                        types.Part.from_function_response(
                            name=call_name,
                            response=(
                                result.model_dump()
                            ),
                        )
                    )

                contents.append(
                    types.Content(
                        role="user",
                        parts=(
                            function_response_parts
                        ),
                    )
                )

            message = (
                "Gemini reached the maximum "
                "agent round budget."
            )

            errors.append(
                message
            )

            return GeminiRunResult(
                status="DEGRADED",
                final_text="",
                rounds=self.max_rounds,
                tool_calls=tool_calls,
                errors=errors,
            )

        except Exception as exc:
            errors.append(
                (
                    "Gemini execution failed: "
                    f"{exc}"
                )
            )

            return GeminiRunResult(
                status="FAILED",
                final_text="",
                rounds=len(
                    tool_calls
                ),
                tool_calls=tool_calls,
                errors=errors,
            )