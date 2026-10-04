from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """
    Standard result envelope for every AERIS tool.

    The agent never receives arbitrary Python objects directly.
    Every tool must return this structured result.
    """

    ok: bool

    tool_name: str

    summary: str

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    error_code: str | None = None

    error_message: str | None = None

    warnings: list[str] = Field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )

    @classmethod
    def success(
        cls,
        *,
        tool_name: str,
        summary: str,
        data: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
    ) -> "ToolResult":
        return cls(
            ok=True,
            tool_name=tool_name,
            summary=summary,
            data=data or {},
            evidence=evidence or [],
            warnings=warnings or [],
        )

    @classmethod
    def failure(
        cls,
        *,
        tool_name: str,
        error_code: str,
        error_message: str,
        summary: str = "Tool execution failed.",
    ) -> "ToolResult":
        return cls(
            ok=False,
            tool_name=tool_name,
            summary=summary,
            error_code=error_code,
            error_message=error_message,
        )


class AerisTool(ABC):
    """
    Base class for every AERIS tool.

    Tools expose:
    - stable name
    - human-readable description
    - JSON-compatible parameter schema
    - deterministic execution interface

    The LLM will eventually consume the definition returned
    by `definition()`.
    """

    name: str
    description: str

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """
        JSON-schema-compatible parameter definition.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Execute the tool.
        """
        raise NotImplementedError

    def definition(self) -> dict[str, Any]:
        """
        Provider-neutral function/tool definition.

        Later this can be translated into Gemini's native
        function declaration format without changing the tools.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }