from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentStage(str, Enum):
    OBSERVE = "OBSERVE"
    DIAGNOSE = "DIAGNOSE"
    PLAN = "PLAN"
    EVALUATE = "EVALUATE"
    STRESS_TEST = "STRESS_TEST"
    CRITIC = "CRITIC"
    RECOMMEND = "RECOMMEND"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REASSESS = "REASSESS"
    COMPLETE = "COMPLETE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    WAITING_HUMAN = "WAITING_HUMAN"
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class InvestigationStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class InvestigationPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AgentEvent(BaseModel):
    sequence: int
    stage: AgentStage
    event_type: str
    message: str

    tool_name: str | None = None
    candidate_id: str | None = None

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    data: dict[str, Any] = Field(
        default_factory=dict
    )


class InvestigationQuestion(BaseModel):
    question_id: str

    question: str

    rationale: str

    tool_name: str

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )

    priority: InvestigationPriority = (
        InvestigationPriority.MEDIUM
    )

    status: InvestigationStatus = (
        InvestigationStatus.PENDING
    )

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    result_summary: str | None = None


class InvestigationPlan(BaseModel):
    objective: str

    questions: list[InvestigationQuestion] = Field(
        default_factory=list
    )

    completeness: float = 0.0

    rationale: str = ""


class CausalNode(BaseModel):
    node_id: str
    node_type: str
    label: str

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class CausalEdge(BaseModel):
    source: str
    target: str
    relationship: str

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class CausalGraph(BaseModel):
    nodes: list[CausalNode] = Field(
        default_factory=list
    )

    edges: list[CausalEdge] = Field(
        default_factory=list
    )


class Diagnosis(BaseModel):
    summary: str

    primary_cause: str

    secondary_causes: list[str] = Field(
        default_factory=list
    )

    affected_flights: list[str] = Field(
        default_factory=list
    )

    affected_sectors: list[str] = Field(
        default_factory=list
    )

    affected_airports: list[str] = Field(
        default_factory=list
    )

    urgency: str = "MEDIUM"

    evidence_completeness: float = 0.0

    causal_chain: list[str] = Field(
        default_factory=list
    )

    causal_graph: CausalGraph = Field(
        default_factory=CausalGraph
    )

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class CriticResult(BaseModel):
    candidate_id: str

    challenged: bool

    severity: str = "LOW"

    finding: str

    trigger_conditions: list[str] = Field(
        default_factory=list
    )

    evidence_ids: list[str] = Field(
        default_factory=list
    )


class ApprovalState(BaseModel):
    required: bool = True

    status: str = "AWAITING_APPROVAL"

    decision: str | None = None

    reason: str | None = None


class Recommendation(BaseModel):
    candidate_id: str

    confidence: float

    summary: str

    why_selected: list[str] = Field(
        default_factory=list
    )

    rejected_candidates: list[dict[str, Any]] = Field(
        default_factory=list
    )

    critic: CriticResult | None = None

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    human_approval_required: bool = True


class AgentState(BaseModel):
    run_id: str

    scenario_id: str

    target_flight_id: str

    stage: AgentStage = AgentStage.OBSERVE

    status: RunStatus = RunStatus.RUNNING

    step: int = 0

    world_state: dict[str, Any] = Field(
        default_factory=dict
    )

    investigation_plan: InvestigationPlan | None = None

    investigation_results: list[dict[str, Any]] = Field(
        default_factory=list
    )

    evidence: list[dict[str, Any]] = Field(
        default_factory=list
    )

    diagnosis: Diagnosis | None = None

    candidates: list[dict[str, Any]] = Field(
        default_factory=list
    )

    feasible_candidates: list[dict[str, Any]] = Field(
        default_factory=list
    )

    simulation_results: list[dict[str, Any]] = Field(
        default_factory=list
    )

    stress_test_results: list[dict[str, Any]] = Field(
        default_factory=list
    )

    leading_candidate_id: str | None = None

    critic_result: CriticResult | None = None

    recommendation: Recommendation | None = None

    approval: ApprovalState = Field(
        default_factory=ApprovalState
    )

    verification_result: dict[str, Any] | None = None

    errors: list[str] = Field(
        default_factory=list
    )

    events: list[AgentEvent] = Field(
        default_factory=list
    )


_ALLOWED_TRANSITIONS: dict[
    AgentStage,
    set[AgentStage]
] = {
    AgentStage.OBSERVE: {
        AgentStage.DIAGNOSE,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.DIAGNOSE: {
        AgentStage.PLAN,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.PLAN: {
        AgentStage.EVALUATE,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.EVALUATE: {
        AgentStage.STRESS_TEST,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.STRESS_TEST: {
        AgentStage.CRITIC,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.CRITIC: {
        AgentStage.RECOMMEND,
        AgentStage.PLAN,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.RECOMMEND: {
        AgentStage.HUMAN_APPROVAL,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.HUMAN_APPROVAL: {
        AgentStage.EXECUTE,
        AgentStage.REASSESS,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.EXECUTE: {
        AgentStage.VERIFY,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.VERIFY: {
        AgentStage.COMPLETE,
        AgentStage.REASSESS,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.REASSESS: {
        AgentStage.DIAGNOSE,
        AgentStage.COMPLETE,
        AgentStage.DEGRADED,
        AgentStage.FAILED,
    },
    AgentStage.COMPLETE: set(),
    AgentStage.DEGRADED: set(),
    AgentStage.FAILED: set(),
}


def can_transition(
    current: AgentStage,
    target: AgentStage,
) -> bool:
    return target in _ALLOWED_TRANSITIONS[
        current
    ]


def transition(
    state: AgentState,
    target: AgentStage,
    message: str,
) -> AgentState:
    if not can_transition(
        state.stage,
        target,
    ):
        raise ValueError(
            "Invalid agent transition: "
            f"{state.stage.value} -> {target.value}"
        )

    state.stage = target
    state.step += 1

    state.events.append(
        AgentEvent(
            sequence=state.step,
            stage=target,
            event_type="STATE_TRANSITION",
            message=message,
        )
    )

    return state


def new_agent_state(
    run_id: str,
    scenario_id: str,
    target_flight_id: str,
) -> AgentState:
    return AgentState(
        run_id=run_id,
        scenario_id=scenario_id,
        target_flight_id=target_flight_id,
    )