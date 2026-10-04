from typing import Any

from .critic import criticise_candidate
from .evidence import EvidenceStore
from .planner import (
    NoFeasibleCandidateError,
    feasible_candidates,
    rejected_candidates,
    select_initial_leader,
)
from .state import (
    AgentEvent,
    AgentStage,
    AgentState,
    RunStatus,
    can_transition,
    new_agent_state,
    transition,
)
from .synthesizer import build_recommendation
from copilot.mock_engine import MockEngineClient
from copilot.tools import (
    ToolResult,
    ToolRegistry,
    build_default_registry,
)


class AgentOrchestrator:
    """
    Phase-2 AERIS orchestration shell.

    The orchestrator never accesses engine internals directly.
    It interacts through the ToolRegistry.

    The current registry uses deterministic mock adapters.
    Later, the same interface will sit on top of the real
    Person-1 engine.
    """

    def __init__(
        self,
        engine: MockEngineClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.engine = (
            engine
            or MockEngineClient()
        )

        self.registry = (
            registry
            or build_default_registry(
                self.engine
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
                "Observation complete; begin causal diagnosis.",
            )

            self._diagnose(
                state
            )

            transition(
                state,
                AgentStage.PLAN,
                "Diagnosis complete; request intervention candidates.",
            )

            self._plan(
                state
            )

            transition(
                state,
                AgentStage.EVALUATE,
                "Candidate set loaded; evaluate hard feasibility.",
            )

            self._evaluate(
                state
            )

            transition(
                state,
                AgentStage.STRESS_TEST,
                "Feasible candidates isolated; collect network and future-state evidence.",
            )

            self._stress_test(
                state
            )

            transition(
                state,
                AgentStage.CRITIC,
                "Evidence collected; challenge preliminary leader.",
            )

            self._critic(
                state
            )

            transition(
                state,
                AgentStage.RECOMMEND,
                "Critic stage complete; synthesize recommendation.",
            )

            self._recommend(
                state
            )

            transition(
                state,
                AgentStage.HUMAN_APPROVAL,
                "Recommendation prepared; waiting for human approval.",
            )

            state.status = RunStatus.WAITING_HUMAN

            return state

        except NoFeasibleCandidateError as exc:
            state.errors.append(
                str(exc)
            )

            state.status = RunStatus.DEGRADED

            if can_transition(
                state.stage,
                AgentStage.DEGRADED,
            ):
                transition(
                    state,
                    AgentStage.DEGRADED,
                    str(exc),
                )

            return state

        except Exception as exc:
            state.errors.append(
                str(exc)
            )

            state.status = RunStatus.FAILED

            if can_transition(
                state.stage,
                AgentStage.FAILED,
            ):
                transition(
                    state,
                    AgentStage.FAILED,
                    f"Fatal orchestration error: {exc}",
                )

            return state

    def _invoke_tool(
        self,
        state: AgentState,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        result = self.registry.invoke(
            tool_name,
            arguments or {},
        )

        if result.ok:
            evidence_ids = []

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

                evidence_ids.append(
                    evidence.evidence_id
                )

            state.events.append(
                self._event(
                    state,
                    "TOOL_RESULT",
                    result.summary,
                    tool_name=result.tool_name,
                    evidence_ids=evidence_ids,
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

        return result

    def _observe(
        self,
        state: AgentState,
    ) -> None:
        airspace = self._invoke_tool(
            state,
            "get_airspace_state",
        )

        disruptions = self._invoke_tool(
            state,
            "get_disruptions",
        )

        target = self._invoke_tool(
            state,
            "get_target_flight",
            {
                "flight_id": state.target_flight_id
            },
        )

        state.world_state = {
            **airspace.data,
            "disruptions": disruptions.data,
            "target": target.data,
        }

        state.events.append(
            self._event(
                state,
                "OBSERVATION_READY",
                (
                    "Airspace, disruption and target-flight "
                    "state have been assembled."
                ),
            )
        )

    def _diagnose(
        self,
        state: AgentState,
    ) -> None:
        world = state.world_state

        alerts = world.get(
            "disruptions",
            {},
        ).get(
            "disruptions",
            [],
        )

        sectors = world.get(
            "sectors",
            [],
        )

        stressed_sectors = [
            sector
            for sector in sectors
            if sector.get(
                "status"
            ) == "STRESSED"
        ]

        airports = world.get(
            "airports",
            [],
        )

        degraded_airports = [
            airport
            for airport in airports
            if airport.get(
                "operational_status"
            ) != "NORMAL"
        ]

        primary_cause = (
            alerts[0].get(
                "type",
                "UNKNOWN_DEGRADATION",
            )
            if alerts
            else "UNKNOWN_DEGRADATION"
        )

        alert_text = (
            alerts[0].get(
                "summary",
                "Operational degradation detected.",
            )
            if alerts
            else "Operational degradation detected."
        )

        affected_sectors = [
            str(
                sector.get(
                    "id"
                )
            )
            for sector
            in stressed_sectors
        ]

        affected_airports = [
            str(
                airport.get(
                    "id"
                )
            )
            for airport
            in degraded_airports
        ]

        evidence = self.evidence.add(
            kind="DIAGNOSIS",
            title="Initial causal diagnosis",
            summary=alert_text,
            source="agent diagnosis",
            severity="HIGH",
            data={
                "primary_cause": primary_cause,
                "affected_sectors": affected_sectors,
                "affected_airports": affected_airports,
            },
        )

        from .state import Diagnosis

        state.diagnosis = Diagnosis(
            summary=alert_text,
            primary_cause=primary_cause,
            secondary_causes=[
                item.get(
                    "type",
                    "UNKNOWN",
                )
                for item in alerts[1:]
            ],
            affected_flights=[
                state.target_flight_id
            ],
            affected_sectors=affected_sectors,
            affected_airports=affected_airports,
            urgency=(
                "HIGH"
                if world.get(
                    "urgency"
                ) == "HIGH"
                else "MEDIUM"
            ),
            evidence_ids=[
                evidence.evidence_id
            ],
        )

        state.events.append(
            self._event(
                state,
                "DIAGNOSIS_READY",
                (
                    "Causal factors and stressed resources "
                    "have been identified."
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _plan(
        self,
        state: AgentState,
    ) -> None:
        result = self._invoke_tool(
            state,
            "generate_alternatives",
            {
                "flight_id": state.target_flight_id
            },
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
                    f"Loaded {len(candidates)} intervention "
                    "candidates for evaluation."
                ),
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

            result = self._invoke_tool(
                state,
                "validate_candidate",
                {
                    "candidate_id": candidate_id
                },
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

        state.feasible_candidates = feasible

        for candidate in rejected:
            candidate_id = str(
                candidate.get(
                    "candidate_id"
                )
            )

            state.events.append(
                self._event(
                    state,
                    "CANDIDATE_REJECTED",
                    (
                        f"{candidate_id} rejected by "
                        "hard-constraint evidence."
                    ),
                    candidate_id=candidate_id,
                )
            )

        if not feasible:
            raise NoFeasibleCandidateError(
                "No safe candidate satisfies current hard constraints."
            )

        leader = select_initial_leader(
            state.candidates
        )

        state.leading_candidate_id = str(
            leader["candidate_id"]
        )

        evidence = self.evidence.add(
            kind="PRELIMINARY_SELECTION",
            title="Preliminary leader selected",
            summary=(
                f"{state.leading_candidate_id} leads on "
                "immediate/local criteria before resilience challenge."
            ),
            source="deterministic planner",
            candidate_id=state.leading_candidate_id,
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
            simulation = self._invoke_tool(
                state,
                "simulate_network_impact",
                {
                    "candidate_id": candidate_id
                },
            )

            simulations.append(
                simulation.data
            )

            stress = self._invoke_tool(
                state,
                "stress_test_candidate",
                {
                    "candidate_id": candidate_id
                },
            )

            stress_results.append(
                stress.data
            )

        state.simulation_results = simulations
        state.stress_test_results = stress_results

        state.events.append(
            self._event(
                state,
                "EVALUATION_COMPLETE",
                (
                    f"Network simulation and stress testing "
                    f"completed for {len(candidate_ids)} candidates."
                ),
            )
        )

    def _critic(
        self,
        state: AgentState,
    ) -> None:
        candidate = (
            self.engine.get_candidate(
                str(
                    state.leading_candidate_id
                )
            )
        )

        stress_result = (
            self.engine.get_stress_result(
                str(
                    state.leading_candidate_id
                )
            )
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
            candidate_id=result.candidate_id,
            severity=result.severity,
            data={
                "challenged": result.challenged,
                "trigger_conditions": (
                    result.trigger_conditions
                ),
            },
        )

        result.evidence_ids = [
            evidence.evidence_id
        ]

        state.critic_result = result

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
        evidence_ids = self.evidence.ids()

        recommendation = (
            build_recommendation(
                candidates=state.candidates,
                critic_result=(
                    state.critic_result
                ),
                evidence_ids=evidence_ids,
            )
        )

        state.recommendation = recommendation

        evidence = self.evidence.add(
            kind="RECOMMENDATION",
            title="Resilient recommendation prepared",
            summary=recommendation.summary,
            source="deterministic synthesizer",
            candidate_id=(
                recommendation.candidate_id
            ),
            data={
                "confidence": (
                    recommendation.confidence
                ),
                "why_selected": (
                    recommendation.why_selected
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

    @staticmethod
    def _event(
        state: AgentState,
        event_type: str,
        message: str,
        *,
        tool_name: str | None = None,
        candidate_id: str | None = None,
        evidence_ids: list[str] | None = None,
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
        )