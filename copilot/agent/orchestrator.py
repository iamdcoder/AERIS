from typing import Any

from .critic import criticise_candidate
from .diagnostics import build_causal_diagnosis
from .evidence import EvidenceStore
from .investigation import (
    build_investigation_plan,
    update_plan_completeness,
)
from .planner import (
    NoFeasibleCandidateError,
    feasible_candidates,
    select_initial_leader,
)
from .state import (
    AgentEvent,
    AgentStage,
    AgentState,
    InvestigationStatus,
    RunStatus,
    can_transition,
    new_agent_state,
    transition,
)
from .synthesizer import build_recommendation
from copilot.mock_engine import MockEngineClient
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)


class AgentOrchestrator:
    """
    AERIS Person-2 orchestration layer.

    The orchestrator talks to capabilities through the
    ToolRegistry rather than directly accessing engine internals.

    The current registry uses deterministic mock tools.
    Future phases can replace those adapters with the real
    Person-1 engine and add Gemini tool selection on top.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
    ) -> None:
        if registry is not None:
            self.registry = registry
        else:
            self.registry = (
                build_default_registry(
                    MockEngineClient()
                )
            )

        self.evidence = EvidenceStore()

    def run_mock_preview(
        self,
        *,
        run_id: str = "RUN-001",
        scenario_id: str = "mumbai_weather_crisis",
        target_flight_id: str = "F102",
    ) -> AgentState:
        state = new_agent_state(
            run_id=run_id,
            scenario_id=scenario_id,
            target_flight_id=target_flight_id,
        )

        try:
            self._observe(
                state
            )

            transition(
                state,
                AgentStage.DIAGNOSE,
                (
                    "Observation complete; "
                    "begin intelligent investigation."
                ),
            )

            self._diagnose(
                state
            )

            transition(
                state,
                AgentStage.PLAN,
                (
                    "Causal diagnosis complete; "
                    "request intervention candidates."
                ),
            )

            self._plan(
                state
            )

            transition(
                state,
                AgentStage.EVALUATE,
                (
                    "Candidate set loaded; "
                    "evaluate hard feasibility."
                ),
            )

            self._evaluate(
                state
            )

            transition(
                state,
                AgentStage.STRESS_TEST,
                (
                    "Feasible candidates isolated; "
                    "collect network and future-state evidence."
                ),
            )

            self._stress_test(
                state
            )

            transition(
                state,
                AgentStage.CRITIC,
                (
                    "Evidence collected; "
                    "challenge preliminary leader."
                ),
            )

            self._critic(
                state
            )

            transition(
                state,
                AgentStage.RECOMMEND,
                (
                    "Critic stage complete; "
                    "synthesize recommendation."
                ),
            )

            self._recommend(
                state
            )

            transition(
                state,
                AgentStage.HUMAN_APPROVAL,
                (
                    "Recommendation prepared; "
                    "waiting for human approval."
                ),
            )

            state.status = (
                RunStatus.WAITING_HUMAN
            )

            self._sync_evidence(
                state
            )

            return state

        except NoFeasibleCandidateError as exc:
            state.errors.append(
                str(exc)
            )

            state.status = (
                RunStatus.DEGRADED
            )

            if can_transition(
                state.stage,
                AgentStage.DEGRADED,
            ):
                transition(
                    state,
                    AgentStage.DEGRADED,
                    str(exc),
                )

            self._sync_evidence(
                state
            )

            return state

        except Exception as exc:
            state.errors.append(
                str(exc)
            )

            state.status = (
                RunStatus.FAILED
            )

            if can_transition(
                state.stage,
                AgentStage.FAILED,
            ):
                transition(
                    state,
                    AgentStage.FAILED,
                    (
                        "Fatal orchestration error: "
                        f"{exc}"
                    ),
                )

            self._sync_evidence(
                state
            )

            return state

    def _invoke_tool(
        self,
        state: AgentState,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ):
        evidence_count_before = len(
            self.evidence.all()
        )

        state.events.append(
            self._event(
                state,
                "TOOL_CALL",
                (
                    f"Calling tool {tool_name}."
                ),
                tool_name=tool_name,
            )
        )

        result = self.registry.invoke(
            tool_name,
            arguments or {},
        )

        new_evidence_ids: list[str] = []

        if result.ok:
            for item in result.evidence:
                evidence = self.evidence.add(
                    kind=str(
                        item.get(
                            "kind",
                            "TOOL_RESULT",
                        )
                    ),
                    title=str(
                        item.get(
                            "title",
                            result.tool_name,
                        )
                    ),
                    summary=str(
                        item.get(
                            "summary",
                            result.summary,
                        )
                    ),
                    source=result.tool_name,
                    candidate_id=item.get(
                        "candidate_id"
                    ),
                    severity=item.get(
                        "severity"
                    ),
                    data=item,
                )

                new_evidence_ids.append(
                    evidence.evidence_id
                )

            state.events.append(
                self._event(
                    state,
                    "TOOL_RESULT",
                    result.summary,
                    tool_name=result.tool_name,
                    evidence_ids=(
                        new_evidence_ids
                    ),
                )

            )

        else:
            state.errors.append(
                (
                    f"{result.tool_name}: "
                    f"{result.error_message}"
                )
            )

            state.events.append(
                self._event(
                    state,
                    "TOOL_ERROR",
                    result.summary,
                    tool_name=result.tool_name,
                )
            )

            raise RuntimeError(
                (
                    f"{result.tool_name} failed: "
                    f"{result.error_message}"
                )
            )

        if (
            len(self.evidence.all())
            < evidence_count_before
        ):
            raise RuntimeError(
                "Evidence store integrity error."
            )

        return result, new_evidence_ids

    def _observe(
        self,
        state: AgentState,
    ) -> None:
        airspace, _ = (
            self._invoke_tool(
                state,
                "get_airspace_state",
            )
        )

        disruptions, _ = (
            self._invoke_tool(
                state,
                "get_disruptions",
            )
        )

        target, _ = (
            self._invoke_tool(
                state,
                "get_target_flight",
                {
                    "flight_id": (
                        state.target_flight_id
                    )
                },
            )
        )

        state.world_state = {
            **airspace.data,
            "disruptions": (
                disruptions.data
            ),
            "target": target.data,
        }

        state.events.append(
            self._event(
                state,
                "OBSERVATION_READY",
                (
                    "Airspace, disruptions and "
                    "target-flight state assembled."
                ),
            )
        )

        self._sync_evidence(
            state
        )

    def _diagnose(
        self,
        state: AgentState,
    ) -> None:
        """
        Build an evidence-driven investigation plan,
        execute the selected tool calls and construct
        a causal diagnosis.
        """

        plan = build_investigation_plan(
            state.world_state
        )

        state.investigation_plan = (
            plan
        )

        state.events.append(
            self._event(
                state,
                "INVESTIGATION_PLAN_CREATED",
                (
                    f"Investigation policy selected "
                    f"{len(plan.questions)} evidence question(s)."
                ),
            )
        )

        for question in plan.questions:
            try:
                result, evidence_ids = (
                    self._invoke_tool(
                        state,
                        question.tool_name,
                        question.arguments,
                    )
                )

                question.status = (
                    InvestigationStatus.COMPLETED
                )

                question.evidence_ids = (
                    evidence_ids
                )

                question.result_summary = (
                    result.summary
                )

                state.investigation_results.append(
                    {
                        "question_id": (
                            question.question_id
                        ),
                        "tool_name": (
                            question.tool_name
                        ),
                        "arguments": (
                            question.arguments
                        ),
                        "status": "COMPLETED",
                        "summary": (
                            result.summary
                        ),
                        "data": result.data,
                        "evidence_ids": (
                            evidence_ids
                        ),
                    }
                )

                state.events.append(
                    self._event(
                        state,
                        "INVESTIGATION_FINDING",
                        (
                            f"{question.question_id}: "
                            f"{result.summary}"
                        ),
                        tool_name=(
                            question.tool_name
                        ),
                        evidence_ids=(
                            evidence_ids
                        ),
                    )
                )

            except Exception as exc:
                question.status = (
                    InvestigationStatus.FAILED
                )

                question.result_summary = str(
                    exc
                )

                state.investigation_results.append(
                    {
                        "question_id": (
                            question.question_id
                        ),
                        "tool_name": (
                            question.tool_name
                        ),
                        "arguments": (
                            question.arguments
                        ),
                        "status": "FAILED",
                        "summary": str(
                            exc
                        ),
                        "data": {},
                        "evidence_ids": [],
                    }
                )

                raise

        update_plan_completeness(
            plan
        )

        state.investigation_plan = (
            plan
        )

        diagnosis = (
            build_causal_diagnosis(
                world_state=(
                    state.world_state
                ),
                investigation_results=(
                    state.investigation_results
                ),
                target_flight_id=(
                    state.target_flight_id
                ),
                evidence_ids=(
                    self.evidence.ids()
                ),
                evidence_completeness=(
                    plan.completeness
                ),
            )
        )

        state.diagnosis = diagnosis

        state.events.append(
            self._event(
                state,
                "DIAGNOSIS_READY",
                diagnosis.summary,
                evidence_ids=(
                    diagnosis.evidence_ids
                ),
                data={
                    "primary_cause": (
                        diagnosis.primary_cause
                    ),
                    "urgency": (
                        diagnosis.urgency
                    ),
                    "evidence_completeness": (
                        diagnosis.evidence_completeness
                    ),
                    "causal_chain": (
                        diagnosis.causal_chain
                    ),
                    "causal_node_count": (
                        len(
                            diagnosis
                            .causal_graph
                            .nodes
                        )
                    ),
                    "causal_edge_count": (
                        len(
                            diagnosis
                            .causal_graph
                            .edges
                        )
                    ),
                },
            )
        )

        self._sync_evidence(
            state
        )

    def _plan(
        self,
        state: AgentState,
    ) -> None:
        result, evidence_ids = (
            self._invoke_tool(
                state,
                "generate_alternatives",
                {
                    "flight_id": (
                        state.target_flight_id
                    )
                },
            )
        )

        candidates = result.data.get(
            "alternatives",
            [],
        )

        state.candidates = candidates

        state.events.append(
            self._event(
                state,
                "CANDIDATES_READY",
                (
                    f"Loaded {len(candidates)} "
                    "intervention candidates."
                ),
                evidence_ids=evidence_ids,
            )
        )

    def _evaluate(
        self,
        state: AgentState,
    ) -> None:
        feasible = []

        rejected = []

        for candidate in state.candidates:
            candidate_id = str(
                candidate.get(
                    "candidate_id"
                )
            )

            result, evidence_ids = (
                self._invoke_tool(
                    state,
                    "validate_candidate",
                    {
                        "candidate_id": (
                            candidate_id
                        )
                    },
                )
            )

            validation = result.data

            if validation.get(
                "feasible"
            ) is True:
                feasible.append(
                    candidate
                )
            else:
                rejected.append(
                    candidate
                )

                state.events.append(
                    self._event(
                        state,
                        "CANDIDATE_REJECTED",
                        (
                            f"{candidate_id} rejected by "
                            "hard-constraint evidence."
                        ),
                        candidate_id=(
                            candidate_id
                        ),
                        evidence_ids=evidence_ids,
                    )
                )

        state.feasible_candidates = (
            feasible
        )

        if not feasible:
            raise NoFeasibleCandidateError(
                (
                    "No safe candidate satisfies "
                    "current hard constraints."
                )
            )

        leader = select_initial_leader(
            state.candidates
        )

        state.leading_candidate_id = str(
            leader[
                "candidate_id"
            ]
        )

        evidence = self.evidence.add(
            kind="PRELIMINARY_SELECTION",
            title="Preliminary leader selected",
            summary=(
                f"{state.leading_candidate_id} leads "
                "on immediate/local criteria before "
                "the resilience challenge."
            ),
            source="deterministic planner",
            candidate_id=(
                state.leading_candidate_id
            ),
            data={
                "local_score": leader.get(
                    "local_score"
                )
            },
        )

        state.events.append(
            self._event(
                state,
                "PRELIMINARY_LEADER",
                (
                    f"Preliminary leader: "
                    f"{state.leading_candidate_id}."
                ),
                candidate_id=(
                    state.leading_candidate_id
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _stress_test(
        self,
        state: AgentState,
    ) -> None:
        candidate_ids = [
            str(
                candidate[
                    "candidate_id"
                ]
            )
            for candidate
            in state.feasible_candidates
        ]

        simulations = []

        stress_results = []

        for candidate_id in candidate_ids:
            simulation, _ = (
                self._invoke_tool(
                    state,
                    "simulate_network_impact",
                    {
                        "candidate_id": (
                            candidate_id
                        )
                    },
                )
            )

            simulations.append(
                simulation.data
            )

            stress, _ = (
                self._invoke_tool(
                    state,
                    "stress_test_candidate",
                    {
                        "candidate_id": (
                            candidate_id
                        )
                    },
                )
            )

            stress_results.append(
                stress.data
            )

        state.simulation_results = (
            simulations
        )

        state.stress_test_results = (
            stress_results
        )

        state.events.append(
            self._event(
                state,
                "EVALUATION_COMPLETE",
                (
                    f"Network simulation and stress testing "
                    f"completed for {len(candidate_ids)} "
                    "feasible candidate(s)."
                ),
            )
        )

    def _critic(
        self,
        state: AgentState,
    ) -> None:
        candidate = next(
            (
                item
                for item in state.candidates
                if item.get(
                    "candidate_id"
                )
                == state.leading_candidate_id
            ),
            None,
        )

        stress_result = next(
            (
                item
                for item in (
                    state.stress_test_results
                )
                if item.get(
                    "candidate_id"
                )
                == state.leading_candidate_id
            ),
            None,
        )

        if candidate is None:
            raise RuntimeError(
                (
                    f"Candidate "
                    f"{state.leading_candidate_id} "
                    "was not found."
                )
            )

        result = criticise_candidate(
            candidate,
            stress_result,
        )

        evidence = self.evidence.add(
            kind="CRITIC",
            title="Recommendation challenge",
            summary=result.finding,
            source="deterministic stress evidence",
            candidate_id=(
                result.candidate_id
            ),
            severity=result.severity,
            data={
                "challenged": (
                    result.challenged
                ),
                "trigger_conditions": (
                    result.trigger_conditions
                ),
            },
        )

        result.evidence_ids = [
            evidence.evidence_id
        ]

        state.critic_result = (
            result
        )

        state.events.append(
            self._event(
                state,
                "CRITIC_COMPLETE",
                result.finding,
                candidate_id=(
                    result.candidate_id
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _recommend(
        self,
        state: AgentState,
    ) -> None:
        recommendation = (
            build_recommendation(
                candidates=(
                    state.candidates
                ),
                critic_result=(
                    state.critic_result
                ),
                evidence_ids=(
                    self.evidence.ids()
                ),
            )
        )

        state.recommendation = (
            recommendation
        )

        evidence = self.evidence.add(
            kind="RECOMMENDATION",
            title=(
                "Resilient recommendation prepared"
            ),
            summary=(
                recommendation.summary
            ),
            source=(
                "deterministic synthesizer"
            ),
            candidate_id=(
                recommendation.candidate_id
            ),
            data={
                "confidence": (
                    recommendation.confidence
                ),
                "why_selected": (
                    recommendation
                    .why_selected
                ),
            },
        )

        recommendation.evidence_ids = [
            *recommendation.evidence_ids,
            evidence.evidence_id,
        ]

        state.leading_candidate_id = (
            recommendation.candidate_id
        )

        state.events.append(
            self._event(
                state,
                "RECOMMENDATION_READY",
                (
                    f"Recommendation prepared: "
                    f"{recommendation.candidate_id}."
                ),
                candidate_id=(
                    recommendation.candidate_id
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _sync_evidence(
        self,
        state: AgentState,
    ) -> None:
        state.evidence = (
            self.evidence.as_dicts()
        )

    @staticmethod
    def _event(
        state: AgentState,
        event_type: str,
        message: str,
        *,
        tool_name: str | None = None,
        candidate_id: str | None = None,
        evidence_ids: list[str] | None = None,
        data: dict[str, Any] | None = None,
    ) -> AgentEvent:
        state.step += 1

        return AgentEvent(
            sequence=state.step,
            stage=state.stage,
            event_type=event_type,
            message=message,
            tool_name=tool_name,
            candidate_id=candidate_id,
            evidence_ids=evidence_ids or [],
            data=data or {},
        )