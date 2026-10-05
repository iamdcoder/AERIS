from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from pydantic import BaseModel

from copilot.agent.approval import (
    ApprovalDecision,
    ApprovalRecord,
)
from copilot.agent.execution import (
    ExecutionResult,
    InterventionExecutor,
)
from copilot.agent.reassessment import (
    CandidateReassessor,
    ReassessmentResult,
)
from copilot.agent.ranker import (
    DecisionRanker,
    RankingSummary,
)
from copilot.agent.scoring import (
    DecisionScoreResult,
)
from copilot.agent.verification import (
    InterventionVerifier,
    VerificationResult,
    VerificationStatus,
)


class DecisionLifecycleResult(BaseModel):
    candidate_id: str
    target_flight_id: str

    approval_decision: str

    execution: Optional[ExecutionResult] = None
    verification: Optional[VerificationResult] = None
    reassessment: Optional[ReassessmentResult] = None

    decision_score_result: Optional[DecisionScoreResult] = None
    ranking_summary: Optional[RankingSummary] = None

    completed: bool
    requires_human_approval: bool

    summary: str


class DecisionLifecycleController:
    """
    End-to-end post-recommendation controller.

    It handles:

        APPROVAL
        -> EXECUTION
        -> VERIFICATION
        -> REASSESSMENT

    It never bypasses the approval gate.
    """

    def __init__(
        self,
        executor: Optional[InterventionExecutor] = None,
        verifier: Optional[InterventionVerifier] = None,
        reassessor: Optional[CandidateReassessor] = None,
        engine: Optional[Any] = None,
        verification_advance_minutes: int = 2,
    ) -> None:
        self.engine = engine

        self.executor = (
            executor
            or InterventionExecutor(
                engine=engine
            )
        )

        self.verification_advance_minutes = max(
            0,
            int(
                verification_advance_minutes
            ),
        )

        self.verifier = (
            verifier
            or InterventionVerifier(
                engine=engine
            )
        )

        self.reassessor = (
            reassessor
            or CandidateReassessor(
                ranker=DecisionRanker()
            )
        )

    def process_approval(
        self,
        approval_record: ApprovalRecord,
        target_flight_id: str,
        candidate: Mapping[str, Any],
        registry: Optional[Any] = None,
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> DecisionLifecycleResult:
        candidate_id = self._candidate_id(
            candidate
        )

        if (
            approval_record.decision
            == ApprovalDecision.REJECTED
        ):
            return DecisionLifecycleResult(
                candidate_id=candidate_id,
                target_flight_id=target_flight_id,
                approval_decision=(
                    approval_record.decision.value
                ),
                completed=False,
                requires_human_approval=False,
                summary=(
                    "Intervention was rejected by the human "
                    "operator. Reassessment is required before "
                    "a new recommendation can be accepted."
                ),
            )

        if (
            approval_record.decision
            != ApprovalDecision.APPROVED
        ):
            return DecisionLifecycleResult(
                candidate_id=candidate_id,
                target_flight_id=target_flight_id,
                approval_decision=(
                    approval_record.decision.value
                ),
                completed=False,
                requires_human_approval=True,
                summary=(
                    "Execution is blocked while human approval "
                    "remains pending."
                ),
            )

        execution = self.executor.execute(
            approval_record=approval_record,
            target_flight_id=target_flight_id,
            candidate=candidate,
            registry=registry,
            simulation=simulation,
        )

        if (
            execution.status.value
            != "EXECUTED"
        ):
            return DecisionLifecycleResult(
                candidate_id=candidate_id,
                target_flight_id=target_flight_id,
                approval_decision="APPROVED",
                execution=execution,
                completed=False,
                requires_human_approval=True,
                summary=(
                    "Human approval was recorded, but "
                    "execution failed."
                ),
            )

        if (
            self.engine is not None
            and self.verification_advance_minutes > 0
        ):
            advance = getattr(
                self.engine,
                "advance_simulation",
                None,
            )

            if callable(advance):
                advance(
                    self.verification_advance_minutes
                )

        verification = self.verifier.verify(
            execution=execution,
            registry=registry,
            simulation=simulation,
        )

        completed = (
            verification.status
            == VerificationStatus.VERIFIED
        )

        return DecisionLifecycleResult(
            candidate_id=candidate_id,
            target_flight_id=target_flight_id,
            approval_decision="APPROVED",
            execution=execution,
            verification=verification,
            completed=completed,
            requires_human_approval=False,
            summary=(
                "Execution and verification completed."
                if completed
                else (
                    "Execution completed, but verification "
                    "requires reassessment."
                )
            ),
        )

    def process_rejection(
        self,
        approval_record: ApprovalRecord,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
        previously_rejected_ids: Optional[
            Iterable[str]
        ] = None,
    ) -> DecisionLifecycleResult:
        if (
            approval_record.decision
            != ApprovalDecision.REJECTED
        ):
            raise ValueError(
                "process_rejection requires a REJECTED approval record."
            )

        reason = (
            approval_record.reason
            or ""
        )

        reassessment = (
            self.reassessor.reassess(
                rejected_candidate_id=(
                    approval_record.candidate_id
                ),
                rejection_reason=reason,
                candidates=candidates,
                simulations=simulations,
                stress_tests=stress_tests,
                previously_rejected_ids=(
                    previously_rejected_ids
                ),
            )
        )

        return DecisionLifecycleResult(
            candidate_id=(
                approval_record.candidate_id
            ),
            target_flight_id=(
                approval_record.target_flight_id
            ),
            approval_decision="REJECTED",
            reassessment=reassessment,
            decision_score_result=(
                reassessment.decision_score_result
            ),
            ranking_summary=(
                reassessment.ranking_summary
            ),
            completed=False,
            requires_human_approval=(
                reassessment.requires_new_approval
            ),
            summary=reassessment.summary,
        )

    def reassess_after_verification_failure(
        self,
        verification: VerificationResult,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
        previously_rejected_ids: Optional[
            Iterable[str]
        ] = None,
    ) -> ReassessmentResult:
        if (
            verification.status
            != VerificationStatus.REASSESSMENT_REQUIRED
        ):
            raise ValueError(
                "Verification must require reassessment before "
                "this method is called."
            )

        reason = (
            verification.reassessment_reason
            or verification.summary
        )

        return self.reassessor.reassess(
            rejected_candidate_id=(
                verification.candidate_id
            ),
            rejection_reason=reason,
            candidates=candidates,
            simulations=simulations,
            stress_tests=stress_tests,
            previously_rejected_ids=(
                previously_rejected_ids
            ),
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
            value = candidate.get(
                key
            )

            if value is not None:
                return str(
                    value
                )

        return "UNKNOWN"