from typing import Any

from .base import AerisTool, ToolResult


class ToolNotFoundError(KeyError):
    pass


class ToolRegistry:
    """
    Provider-neutral registry containing all available AERIS tools.

    Security-sensitive stage permissions are enforced by
    GuardedToolRegistry, not by this base registry.
    """

    def __init__(
        self,
        tools: list[AerisTool] | None = None,
    ) -> None:
        self._tools: dict[
            str,
            AerisTool,
        ] = {}

        for tool in tools or []:
            self.register(
                tool
            )

    def register(
        self,
        tool: AerisTool,
    ) -> None:
        if not tool.name:
            raise ValueError(
                "A tool must have a non-empty name."
            )

        if tool.name in self._tools:
            raise ValueError(
                f"Tool already registered: {tool.name}"
            )

        self._tools[
            tool.name
        ] = tool

    def get(
        self,
        tool_name: str,
    ) -> AerisTool:
        try:
            return self._tools[
                tool_name
            ]
        except KeyError as exc:
            raise ToolNotFoundError(
                f"Unknown AERIS tool: {tool_name}"
            ) from exc

    def list_tools(
        self,
    ) -> list[AerisTool]:
        return list(
            self._tools.values()
        )

    def definitions(
        self,
    ) -> list[dict[str, Any]]:
        return [
            tool.definition()
            for tool
            in self._tools.values()
        ]

    def function_declarations(
        self,
    ) -> list[dict[str, Any]]:
        return [
            {
                "name": definition[
                    "name"
                ],
                "description": definition[
                    "description"
                ],
                "parameters": definition[
                    "parameters"
                ],
            }
            for definition
            in self.definitions()
        ]

    def invoke(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        arguments = arguments or {}

        try:
            tool = self.get(
                tool_name
            )

        except ToolNotFoundError as exc:
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="TOOL_NOT_FOUND",
                error_message=str(
                    exc
                ),
            )

        try:
            return tool.execute(
                **arguments
            )

        except TypeError as exc:
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="INVALID_ARGUMENTS",
                error_message=str(
                    exc
                ),
                summary=(
                    "Tool arguments did not match "
                    "the expected interface."
                ),
            )

        except Exception as exc:
            return ToolResult.failure(
                tool_name=tool_name,
                error_code="TOOL_EXECUTION_ERROR",
                error_message=str(
                    exc
                ),
            )