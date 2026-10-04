from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.approval import (
    ApprovalDecision,
    ApprovalRecord,
)


class ExecutionStatus(str, Enum):
    BLOCKED = "BLOCKED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class ExecutionMode(str, Enum):
    ENGINE = "ENGINE"
    SIMULATION_FALLBACK = "SIMULATION_FALLBACK"


class ExecutionRequest(BaseModel):
    candidate_id: str
    target_flight_id: str
    approval_record_id: str
    approved_by: str

    intervention: Dict[str, Any] = Field(
        default_factory=dict
    )


class ExecutionResult(BaseModel):
    candidate_id: str
    target_flight_id: str

    status: ExecutionStatus
    mode: ExecutionMode

    approval_verified: bool

    summary: str

    before_state: Dict[str, Any] = Field(
        default_factory=dict
    )

    after_state: Dict[str, Any] = Field(
        default_factory=dict
    )

    tool_name: Optional[str] = None

    tool_data: Dict[str, Any] = Field(
        default_factory=dict
    )

    error_message: Optional[str] = None


class InterventionExecutor:
    """
    Human-approved execution boundary.

    Gemini never reaches this class directly.

    Once a human approval record exists, the executor can use the
    deterministic engine adapter directly. If no engine is supplied,
    deterministic simulation fallback remains available.
    """

    def __init__(
        self,
        engine: Optional[Any] = None,
    ) -> None:
        self.engine = engine

    def execute(
        self,
        approval_record: ApprovalRecord,
        target_flight_id: str,
        candidate: Mapping[str, Any],
        registry: Optional[Any] = None,
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionResult:
        candidate_id = self._candidate_id(
            candidate
        )

        if (
            approval_record.decision
            != ApprovalDecision.APPROVED
        ):
            return ExecutionResult(
                candidate_id=candidate_id,
                target_flight_id=target_flight_id,
                status=ExecutionStatus.BLOCKED,
                mode=ExecutionMode.SIMULATION_FALLBACK,
                approval_verified=False,
                summary=(
                    "Execution blocked because explicit human "
                    "approval was not recorded."
                ),
                error_message=(
                    "Human approval is required before execution."
                ),
            )

        if (
            approval_record.candidate_id
            != candidate_id
        ):
            return ExecutionResult(
                candidate_id=candidate_id,
                target_flight_id=target_flight_id,
                status=ExecutionStatus.BLOCKED,
                mode=ExecutionMode.SIMULATION_FALLBACK,
                approval_verified=False,
                summary=(
                    "Execution blocked because the approved "
                    "candidate does not match the execution candidate."
                ),
                error_message=(
                    "Approved candidate mismatch."
                ),
            )

        if self.engine is not None:
            engine_result = (
                self._execute_with_engine(
                    approval_record=approval_record,
                    target_flight_id=target_flight_id,
                    candidate=candidate,
                )
            )

            if engine_result is not None:
                return engine_result

        if registry is not None:
            engine_result = (
                self._try_engine_execution(
                    registry=registry,
                    approval_record=approval_record,
                    target_flight_id=target_flight_id,
                    candidate=candidate,
                )
            )

            if engine_result is not None:
                return engine_result

        return self._simulation_fallback(
            approval_record=approval_record,
            target_flight_id=target_flight_id,
            candidate=candidate,
            simulation=simulation or {},
        )

    def _execute_with_engine(
        self,
        approval_record: ApprovalRecord,
        target_flight_id: str,
        candidate: Mapping[str, Any],
    ) -> Optional[ExecutionResult]:
        try:
            result = self.engine.apply_intervention(
                approval_record.candidate_id
            )
        except Exception as exc:
            return ExecutionResult(
                candidate_id=(
                    approval_record.candidate_id
                ),
                target_flight_id=target_flight_id,
                status=ExecutionStatus.FAILED,
                mode=ExecutionMode.ENGINE,
                approval_verified=True,
                summary=(
                    "The human-approved intervention reached "
                    "the deterministic engine but execution failed."
                ),
                tool_name="engine.apply_intervention",
                error_message=str(exc),
            )

        data = (
            result
            if isinstance(result, dict)
            else {}
        )

        return ExecutionResult(
            candidate_id=(
                approval_record.candidate_id
            ),
            target_flight_id=target_flight_id,
            status=ExecutionStatus.EXECUTED,
            mode=ExecutionMode.ENGINE,
            approval_verified=True,
            summary=(
                "Human-approved intervention was applied "
                "through the deterministic engine adapter."
            ),
            after_state=data,
            tool_name="engine.apply_intervention",
            tool_data=data,
        )

    def _try_engine_execution(
        self,
        registry: Any,
        approval_record: ApprovalRecord,
        target_flight_id: str,
        candidate: Mapping[str, Any],
    ) -> Optional[ExecutionResult]:
        arguments = {
            "candidate_id": (
                approval_record.candidate_id
            ),
            "flight_id": target_flight_id,
            "approved_by": (
                approval_record.decided_by
            ),
            "approval_id": (
                approval_record.recommendation_id
            ),
            "candidate": dict(candidate),
        }

        try:
            result = registry.invoke(
                "apply_intervention",
                arguments,
            )
        except (
            KeyError,
            AttributeError,
            TypeError,
            RuntimeError,
        ):
            return None

        if not self._tool_ok(result):
            return ExecutionResult(
                candidate_id=(
                    approval_record.candidate_id
                ),
                target_flight_id=target_flight_id,
                status=ExecutionStatus.FAILED,
                mode=ExecutionMode.ENGINE,
                approval_verified=True,
                summary=(
                    "The approved intervention reached the "
                    "engine adapter but execution failed."
                ),
                tool_name="apply_intervention",
                tool_data=self._tool_data(result),
                error_message=self._tool_error(
                    result
                ),
            )

        data = self._tool_data(
            result
        )

        return ExecutionResult(
            candidate_id=(
                approval_record.candidate_id
            ),
            target_flight_id=target_flight_id,
            status=ExecutionStatus.EXECUTED,
            mode=ExecutionMode.ENGINE,
            approval_verified=True,
            summary=(
                "Human-approved intervention executed through "
                "the deterministic engine adapter."
            ),
            after_state=data,
            tool_name="apply_intervention",
            tool_data=data,
        )

    def _simulation_fallback(
        self,
        approval_record: ApprovalRecord,
        target_flight_id: str,
        candidate: Mapping[str, Any],
        simulation: Mapping[str, Any],
    ) -> ExecutionResult:
        candidate_id = self._candidate_id(
            candidate
        )

        after_state = {
            key: value
            for key, value in simulation.items()
            if key not in {
                "candidate_id",
                "flight_id",
            }
        }

        return ExecutionResult(
            candidate_id=candidate_id,
            target_flight_id=target_flight_id,
            status=ExecutionStatus.EXECUTED,
            mode=ExecutionMode.SIMULATION_FALLBACK,
            approval_verified=True,
            summary=(
                "Human-approved intervention applied to "
                "the deterministic simulated scenario."
            ),
            before_state={
                "candidate_id": candidate_id,
                "flight_id": target_flight_id,
            },
            after_state=after_state,
            tool_data={
                "mode": "SIMULATION_FALLBACK",
                "source": (
                    "deterministic network simulation"
                ),
            },
        )

    @staticmethod
    def _candidate_id(
        candidate: Mapping[str, Any],
    ) -> str:
        for key in (
            "candidate_id",
            "id",
            "route_id",
            "alternative_id",
        ):
            value = candidate.get(key)

            if value is not None:
                return str(value)

        return "UNKNOWN"

    @staticmethod
    def _tool_ok(
        result: Any,
    ) -> bool:
        if result is None:
            return False

        if hasattr(
            result,
            "ok",
        ):
            return bool(result.ok)

        if isinstance(
            result,
            dict,
        ):
            return bool(
                result.get(
                    "ok",
                    False,
                )
            )

        return False

    @staticmethod
    def _tool_data(
        result: Any,
    ) -> Dict[str, Any]:
        if hasattr(
            result,
            "data",
        ):
            data = result.data
            return (
                data
                if isinstance(
                    data,
                    dict,
                )
                else {}
            )

        if isinstance(
            result,
            dict,
        ):
            data = result.get(
                "data",
                {},
            )

            return (
                data
                if isinstance(
                    data,
                    dict,
                )
                else {}
            )

        return {}

    @staticmethod
    def _tool_error(
        result: Any,
    ) -> Optional[str]:
        if result is None:
            return (
                "Engine returned no execution result."
            )

        if hasattr(
            result,
            "error_message",
        ):
            if result.error_message:
                return str(
                    result.error_message
                )

        if isinstance(
            result,
            dict,
        ):
            return str(
                result.get(
                    "error_message",
                    result.get(
                        "error",
                        "Engine execution failed.",
                    ),
                )
            )

        return "Engine execution failed."