from copilot.engine.client import EngineClient, RealEngineClient

from .airspace_tools import build_airspace_tools
from .base import AerisTool, ToolResult
from .registry import (
    ToolNotFoundError,
    ToolRegistry,
)
from .route_tools import build_route_tools
from .scenario_tools import build_scenario_tools
from .simulation_tools import build_simulation_tools


def build_default_registry(
    engine: EngineClient | None = None,
) -> ToolRegistry:
    if engine is None:
        engine = RealEngineClient()

    registry = ToolRegistry()

    tool_builders = [
        build_airspace_tools,
        build_route_tools,
        build_simulation_tools,
        build_scenario_tools,
    ]

    for builder in tool_builders:
        for tool in builder(engine):
            registry.register(tool)

    return registry


__all__ = [
    "AerisTool",
    "ToolResult",
    "ToolRegistry",
    "ToolNotFoundError",
    "EngineClient",
    "RealEngineClient",
    "build_default_registry",
]