from .state import AgentStage, AgentState, RunStatus


__all__ = [
    "AgentOrchestrator",
    "GeminiInvestigator",
    "InvestigationRunResult",
    "AgentStage",
    "AgentState",
    "RunStatus",
]


def __getattr__(name):
    if name == "AgentOrchestrator":
        from .orchestrator import AgentOrchestrator

        return AgentOrchestrator

    if name in {
        "GeminiInvestigator",
        "InvestigationRunResult",
    }:
        from .gemini_runner import (
            GeminiInvestigator,
            InvestigationRunResult,
        )

        return {
            "GeminiInvestigator": GeminiInvestigator,
            "InvestigationRunResult": InvestigationRunResult,
        }[name]

    raise AttributeError(name)