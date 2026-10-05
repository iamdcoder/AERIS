from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ApprovalDecision(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalRequest(BaseModel):
    recommendation_id: str
    candidate_id: str
    target_flight_id: str

    explanation: str

    requested_by: str = "AERIS"
    requires_human_action: bool = True


class ApprovalRecord(BaseModel):
    recommendation_id: str
    candidate_id: str
    target_flight_id: str

    decision: ApprovalDecision = ApprovalDecision.PENDING

    reason: Optional[str] = None
    decided_by: Optional[str] = None

    requested_at_sequence: int = 0
    decided_at_sequence: Optional[int] = None


class ApprovalController:
    """
    Human-in-the-loop gate.

    This controller deliberately separates:
        RECOMMEND
        HUMAN DECISION
        EXECUTION

    It never executes an intervention itself.
    """

    def __init__(self) -> None:
        self._sequence = 0
        self._active_request: Optional[ApprovalRequest] = None
        self._record: Optional[ApprovalRecord] = None
        self._history: List[ApprovalRecord] = []

    @property
    def active_request(self) -> Optional[ApprovalRequest]:
        return self._active_request

    @property
    def current_record(self) -> Optional[ApprovalRecord]:
        return self._record

    @property
    def history(self) -> List[ApprovalRecord]:
        return list(self._history)

    @property
    def is_pending(self) -> bool:
        return (
            self._record is not None
            and self._record.decision
            == ApprovalDecision.PENDING
        )

    @property
    def is_approved(self) -> bool:
        return (
            self._record is not None
            and self._record.decision
            == ApprovalDecision.APPROVED
        )

    @property
    def is_rejected(self) -> bool:
        return (
            self._record is not None
            and self._record.decision
            == ApprovalDecision.REJECTED
        )

    def request(
        self,
        recommendation_id: str,
        candidate_id: str,
        target_flight_id: str,
        explanation: str,
    ) -> ApprovalRequest:
        if self.is_pending:
            raise RuntimeError(
                "An approval request is already pending."
            )

        self._sequence += 1

        request = ApprovalRequest(
            recommendation_id=recommendation_id,
            candidate_id=candidate_id,
            target_flight_id=target_flight_id,
            explanation=explanation,
        )

        self._active_request = request

        self._record = ApprovalRecord(
            recommendation_id=recommendation_id,
            candidate_id=candidate_id,
            target_flight_id=target_flight_id,
            decision=ApprovalDecision.PENDING,
            requested_at_sequence=self._sequence,
        )

        return request

    def approve(
        self,
        decided_by: str = "human_dispatcher",
    ) -> ApprovalRecord:
        self._ensure_pending()

        self._sequence += 1

        assert self._record is not None

        self._record.decision = ApprovalDecision.APPROVED
        self._record.decided_by = decided_by
        self._record.decided_at_sequence = self._sequence

        finalized = self._record.model_copy(deep=True)

        self._history.append(finalized)

        return finalized

    def reject(
        self,
        reason: str,
        decided_by: str = "human_dispatcher",
    ) -> ApprovalRecord:
        self._ensure_pending()

        cleaned_reason = reason.strip()

        if not cleaned_reason:
            raise ValueError(
                "A rejection reason is required."
            )

        self._sequence += 1

        assert self._record is not None

        self._record.decision = ApprovalDecision.REJECTED
        self._record.reason = cleaned_reason
        self._record.decided_by = decided_by
        self._record.decided_at_sequence = self._sequence

        finalized = self._record.model_copy(deep=True)

        self._history.append(finalized)

        return finalized

    def clear(self) -> None:
        self._active_request = None
        self._record = None

    def reset_for_reassessment(self) -> None:
        """
        Clears only the active approval request.

        Historical decisions are preserved.
        """

        self.clear()

    def _ensure_pending(self) -> None:
        if not self.is_pending:
            raise RuntimeError(
                "There is no pending human approval request."
            )