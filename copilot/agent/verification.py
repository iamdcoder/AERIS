from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.execution import ExecutionResult, ExecutionStatus


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    REASSESSMENT_REQUIRED = "REASSESSMENT_REQUIRED"
    FAILED = "FAILED"


class VerificationResult(BaseModel):
    candidate_id: str
    target_flight_id: str

    status: VerificationStatus

    summary: str

    before_metrics: Dict[str, Any] = Field(
        default_factory=dict
    )

    after_metrics: Dict[str, Any] = Field(
        default_factory=dict
    )

    checks: Dict[str, bool] = Field(
        default_factory=dict
    )

    failed_checks: list[str] = Field(
        default_factory=list
    )

    source: str

    reassessment_reason: Optional[str] = None


class InterventionVerifier:
    """
    Post-decision verification layer.

    Preferred path:
        deterministic engine verification tool.

    Current mock-compatible path:
        deterministic checks against the already-computed network
        simulation outcome.

    This lets the project demonstrate the full lifecycle now without
    inventing a real aviation-control interface.
    """

    VERIFY_TOOL_NAME = "verify_intervention"

    def verify(
        self,
        execution: ExecutionResult,
        registry: Optional[Any] = None,
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> VerificationResult:
        if execution.status != ExecutionStatus.EXECUTED:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "Verification could not proceed because "
                    "the intervention was not executed."
                ),
                source="execution_guard",
                reassessment_reason=(
                    "Execution did not complete."
                ),
            )

        if registry is not None:
            engine_result = self._try_engine_verification(
                execution=execution,
                registry=registry,
            )

            if engine_result is not None:
                return engine_result

        return self._deterministic_verification(
            execution=execution,
            simulation=simulation or execution.after_state,
        )

    def _try_engine_verification(
        self,
        execution: ExecutionResult,
        registry: Any,
    ) -> Optional[VerificationResult]:
        arguments = {
            "candidate_id": execution.candidate_id,
            "flight_id": execution.target_flight_id,
        }

        try:
            result = registry.invoke(
                self.VERIFY_TOOL_NAME,
                arguments,
            )
        except (
            KeyError,
            AttributeError,
            TypeError,
            RuntimeError,
        ):
            return None

        ok = self._tool_ok(result)
        data = self._tool_data(result)

        if not ok:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "Engine verification failed after execution."
                ),
                after_metrics=data,
                source="deterministic engine",
                reassessment_reason=(
                    self._tool_error(result)
                    or "Verification tool failed."
                ),
            )

        verified = self._verified_flag(data)

        if verified is False:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.REASSESSMENT_REQUIRED,
                summary=(
                    "The engine reports that the applied intervention "
                    "did not leave the network in the desired state."
                ),
                after_metrics=data,
                source="deterministic engine",
                reassessment_reason=(
                    "Post-execution verification detected degradation."
                ),
            )

        return VerificationResult(
            candidate_id=execution.candidate_id,
            target_flight_id=execution.target_flight_id,
            status=VerificationStatus.VERIFIED,
            summary=(
                "The deterministic engine verified the "
                "human-approved intervention."
            ),
            before_metrics=execution.before_state,
            after_metrics=data,
            checks={
                "engine_verified": True,
            },
            source="deterministic engine",
        )

    def _deterministic_verification(
        self,
        execution: ExecutionResult,
        simulation: Mapping[str, Any],
    ) -> VerificationResult:
        network_delay = self._number(
            simulation,
            (
                "network_delay_delta_min",
                "network_delay_change_min",
                "network_delay",
            ),
        )

        peak_sector_utilization = self._number(
            simulation,
            (
                "peak_sector_utilization",
                "max_sector_utilization",
                "sector_peak_utilization",
            ),
        )

        new_conflicts = self._number(
            simulation,
            (
                "new_conflicts",
                "new_conflict_count",
                "conflict_count",
            ),
        )

        fuel_margin = self._number(
            simulation,
            (
                "fuel_margin_kg",
                "fuel_margin",
                "reserve_margin_kg",
            ),
        )

        downstream_risk = self._text(
            simulation,
            (
                "downstream_risk",
                "downstream_impact",
                "cascade_level",
            ),
        )

        checks: Dict[str, bool] = {}
        failed_checks: list[str] = []

        if new_conflicts is not None:
            checks["no_new_conflicts"] = (
                new_conflicts == 0
            )

            if not checks["no_new_conflicts"]:
                failed_checks.append(
                    "new_conflicts"
                )

        if peak_sector_utilization is not None:
            checks["sector_capacity_safe"] = (
                peak_sector_utilization < 1.0
            )

            if not checks["sector_capacity_safe"]:
                failed_checks.append(
                    "sector_capacity"
                )

        if fuel_margin is not None:
            checks["fuel_margin_safe"] = (
                fuel_margin > 0
            )

            if not checks["fuel_margin_safe"]:
                failed_checks.append(
                    "fuel_margin"
                )

        if downstream_risk is not None:
            normalized = downstream_risk.lower()

            checks["downstream_risk_acceptable"] = (
                normalized
                not in {
                    "critical",
                    "high",
                    "severe",
                }
            )

            if not checks["downstream_risk_acceptable"]:
                failed_checks.append(
                    "downstream_risk"
                )

        if network_delay is not None:
            checks["network_not_worsened"] = (
                network_delay <= 0
            )

            if not checks["network_not_worsened"]:
                failed_checks.append(
                    "network_delay"
                )

        if not checks:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "No deterministic post-execution metrics were "
                    "available for verification."
                ),
                before_metrics=execution.before_state,
                after_metrics=dict(simulation),
                source="deterministic simulation",
                reassessment_reason=(
                    "Verification lacked sufficient evidence."
                ),
            )

        if failed_checks:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.REASSESSMENT_REQUIRED,
                summary=(
                    "Post-execution verification detected "
                    "network degradation or a failed safety check."
                ),
                before_metrics=execution.before_state,
                after_metrics=dict(simulation),
                checks=checks,
                failed_checks=failed_checks,
                source="deterministic simulation",
                reassessment_reason=(
                    "Failed verification checks: "
                    + ", ".join(failed_checks)
                ),
            )

        return VerificationResult(
            candidate_id=execution.candidate_id,
            target_flight_id=execution.target_flight_id,
            status=VerificationStatus.VERIFIED,
            summary=(
                "The deterministic simulated network remains "
                "within the evaluated safety checks after execution."
            ),
            before_metrics=execution.before_state,
            after_metrics=dict(simulation),
            checks=checks,
            failed_checks=[],
            source="deterministic simulation",
        )

    @staticmethod
    def _number(
        source: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> Optional[float]:
        for key in keys:
            value = source.get(key)

            if value is None:
                continue

            try:
                return float(value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _text(
        source: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> Optional[str]:
        for key in keys:
            value = source.get(key)

            if value is not None:
                return str(value)

        return None

    @staticmethod
    def _verified_flag(
        data: Mapping[str, Any],
    ) -> Optional[bool]:
        for key in (
            "verified",
            "verification_passed",
            "safe",
        ):
            if key not in data:
                continue

            value = data[key]

            if isinstance(value, bool):
                return value

            if isinstance(value, str):
                normalized = value.lower().strip()

                if normalized in {
                    "true",
                    "yes",
                    "verified",
                    "safe",
                }:
                    return True

                if normalized in {
                    "false",
                    "no",
                    "failed",
                    "unsafe",
                }:
                    return False

        return None

    @staticmethod
    def _tool_ok(
        result: Any,
    ) -> bool:
        if result is None:
            return False

        if hasattr(result, "ok"):
            return bool(result.ok)

        if isinstance(result, dict):
            return bool(result.get("ok", False))

        return False

    @staticmethod
    def _tool_data(
        result: Any,
    ) -> Dict[str, Any]:
        if hasattr(result, "data"):
            data = result.data

            return data if isinstance(data, dict) else {}

        if isinstance(result, dict):
            data = result.get("data", {})

            return data if isinstance(data, dict) else {}

        return {}

    @staticmethod
    def _tool_error(
        result: Any,
    ) -> Optional[str]:
        if result is None:
            return None

        if hasattr(result, "error_message"):
            if result.error_message:
                return str(result.error_message)

        if isinstance(result, dict):
            value = result.get("error_message")

            if value:
                return str(value)

        return None