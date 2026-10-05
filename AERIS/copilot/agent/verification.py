from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.execution import (
    ExecutionResult,
    ExecutionStatus,
)


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

    source: str = ""

    reassessment_reason: Optional[str] = None


class InterventionVerifier:
    """
    Post-action verifier.

    When connected to the deterministic engine, the engine's actual
    verification result is authoritative.

    Without an engine, previously-computed deterministic simulation
    evidence remains available as the fallback path.
    """

    def __init__(
        self,
        engine: Optional[Any] = None,
    ) -> None:
        self.engine = engine

    def verify(
        self,
        execution: ExecutionResult,
        registry: Optional[Any] = None,
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> VerificationResult:
        if (
            execution.status
            != ExecutionStatus.EXECUTED
        ):
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

        if self.engine is not None:
            result = (
                self._verify_with_engine(
                    execution
                )
            )

            if result is not None:
                return result

        if registry is not None:
            result = (
                self._try_engine_verification(
                    execution=execution,
                    registry=registry,
                )
            )

            if result is not None:
                return result

        return self._deterministic_verification(
            execution=execution,
            simulation=(
                simulation
                or execution.after_state
            ),
        )

    def _verify_with_engine(
        self,
        execution: ExecutionResult,
    ) -> Optional[VerificationResult]:
        try:
            data = self.engine.verify_state(
                execution.candidate_id
            )
        except Exception as exc:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "The deterministic engine could not "
                    "complete post-action verification."
                ),
                source="deterministic engine",
                reassessment_reason=str(exc),
            )

        status = str(
            data.get(
                "status",
                "",
            )
        ).upper()

        if status == "VERIFIED":
            verification_status = (
                VerificationStatus.VERIFIED
            )

        elif status == "REASSESSMENT_REQUIRED":
            verification_status = (
                VerificationStatus.REASSESSMENT_REQUIRED
            )

        else:
            verification_status = (
                VerificationStatus.FAILED
            )

        failed_checks = []

        if not data.get(
            "constraints_safe",
            True,
        ):
            failed_checks.append(
                "constraints_safe"
            )

        if data.get(
            "new_degradation",
            False,
        ):
            failed_checks.append(
                "new_degradation"
            )

        checks = {
            "constraints_safe": bool(
                data.get(
                    "constraints_safe",
                    True,
                )
            ),
            "no_new_degradation": not bool(
                data.get(
                    "new_degradation",
                    False,
                )
            ),
            "reassessment_required": not bool(
                data.get(
                    "reassessment_required",
                    False,
                )
            ),
        }

        return VerificationResult(
            candidate_id=execution.candidate_id,
            target_flight_id=execution.target_flight_id,
            status=verification_status,
            summary=(
                (
                    "The deterministic engine verified the "
                    "human-approved intervention."
                )
                if verification_status
                == VerificationStatus.VERIFIED
                else (
                    "The deterministic engine detected a "
                    "post-action condition requiring reassessment."
                )
                if verification_status
                == VerificationStatus.REASSESSMENT_REQUIRED
                else (
                    "The deterministic engine could not "
                    "verify the intervention."
                )
            ),
            before_metrics=(
                execution.before_state
            ),
            after_metrics=dict(
                data
            ),
            checks=checks,
            failed_checks=failed_checks,
            source="deterministic engine",
            reassessment_reason=(
                "Verification detected a condition that "
                "requires reassessment."
                if verification_status
                == VerificationStatus.REASSESSMENT_REQUIRED
                else None
            ),
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
                "verify_intervention",
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
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "Engine verification failed after execution."
                ),
                after_metrics=self._tool_data(
                    result
                ),
                source="deterministic engine",
                reassessment_reason=(
                    self._tool_error(result)
                ),
            )

        data = self._tool_data(
            result
        )

        verified = data.get(
            "verified"
        )

        if verified is False:
            status = (
                VerificationStatus.REASSESSMENT_REQUIRED
            )
        else:
            status = (
                VerificationStatus.VERIFIED
            )

        return VerificationResult(
            candidate_id=execution.candidate_id,
            target_flight_id=execution.target_flight_id,
            status=status,
            summary=(
                "The deterministic engine verified the "
                "human-approved intervention."
                if status
                == VerificationStatus.VERIFIED
                else (
                    "The engine reports that the applied "
                    "intervention requires reassessment."
                )
            ),
            before_metrics=execution.before_state,
            after_metrics=data,
            checks={
                "engine_verified": (
                    status
                    == VerificationStatus.VERIFIED
                )
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

        if (
            peak_sector_utilization is not None
            and peak_sector_utilization > 1
        ):
            peak_sector_utilization /= 100

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
            normalized = (
                downstream_risk.lower()
            )

            checks[
                "downstream_risk_acceptable"
            ] = normalized not in {
                "critical",
                "high",
                "severe",
            }

            if not checks[
                "downstream_risk_acceptable"
            ]:
                failed_checks.append(
                    "downstream_risk"
                )

        if network_delay is not None:
            checks[
                "network_not_worsened"
            ] = (
                network_delay <= 0
            )

            if not checks[
                "network_not_worsened"
            ]:
                failed_checks.append(
                    "network_delay"
                )

        if not checks:
            return VerificationResult(
                candidate_id=execution.candidate_id,
                target_flight_id=execution.target_flight_id,
                status=VerificationStatus.FAILED,
                summary=(
                    "No deterministic post-execution metrics "
                    "were available for verification."
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
            except (
                TypeError,
                ValueError,
            ):
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
    def _tool_ok(
        result: Any,
    ) -> bool:
        if result is None:
            return False

        if hasattr(
            result,
            "ok",
        ):
            return bool(
                result.ok
            )

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
                "Verification engine returned no result."
            )

        if hasattr(
            result,
            "error_message",
        ):
            if result.error_message:
                return str(
                    result.error_message
                )

        return "Verification engine failed."