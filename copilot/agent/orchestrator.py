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


class AgentOrchestrator:
    """
    Deterministic Phase-1 orchestration shell.

    This version intentionally uses the mock engine.
    Later phases will replace direct fixture access with
    contract-bound tools and add Gemini-based reasoning.
    """

    def __init__(
        self,
        engine: MockEngineClient | None = None,
    ) -> None:
        self.engine = (
            engine
            or MockEngineClient()
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
            self._observe(state)

            transition(
                state,
                AgentStage.DIAGNOSE,
                "Observation complete; begin causal diagnosis.",
            )

            self._diagnose(state)

            transition(
                state,
                AgentStage.PLAN,
                "Diagnosis complete; request intervention candidates.",
            )

            self._plan(state)

            transition(
                state,
                AgentStage.EVALUATE,
                "Candidate set loaded; evaluate hard feasibility.",
            )

            self._evaluate(state)

            transition(
                state,
                AgentStage.STRESS_TEST,
                "Feasible candidates isolated; collect future-state evidence.",
            )

            self._stress_test(state)

            transition(
                state,
                AgentStage.CRITIC,
                "Stress-test evidence collected; challenge preliminary leader.",
            )

            self._critic(state)

            transition(
                state,
                AgentStage.RECOMMEND,
                "Critic stage complete; synthesize recommendation.",
            )

            self._recommend(state)

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

            if (
                state.stage
                not in (
                    AgentStage.DEGRADED,
                    AgentStage.FAILED,
                )
            ):
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

            if (
                state.stage
                not in (
                    AgentStage.FAILED,
                    AgentStage.DEGRADED,
                )
            ):
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

    def _observe(
        self,
        state: AgentState,
    ) -> None:
        state.world_state = (
            self.engine.get_state()
        )

        evidence = self.evidence.add(
            kind="OBSERVATION",
            title="Airspace state loaded",
            summary=(
                f"Loaded deterministic simulated state "
                f"at T+{state.world_state.get('simulation_time_min', 0)} min "
                f"for target flight {state.target_flight_id}."
            ),
            source="mock_engine/state.json",
            data={
                "simulation_time_min": (
                    state.world_state.get(
                        "simulation_time_min"
                    )
                ),
                "active_aircraft": (
                    state.world_state.get(
                        "network_summary",
                        {},
                    ).get(
                        "active_aircraft"
                    )
                ),
            },
        )

        state.events.append(
            self._event(
                state,
                "OBSERVATION_READY",
                "Current world state is available to the orchestrator.",
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _diagnose(
        self,
        state: AgentState,
    ) -> None:
        world = state.world_state

        alerts = world.get(
            "alerts",
            [],
        )

        sectors = [
            item
            for item in world.get(
                "sectors",
                [],
            )
            if item.get(
                "status"
            ) == "STRESSED"
        ]

        airports = [
            item
            for item in world.get(
                "airports",
                [],
            )
            if item.get(
                "operational_status"
            ) != "NORMAL"
        ]

        primary_cause = (
            alerts[0].get(
                "type",
                "unknown_degradation",
            )
            if alerts
            else "unknown_degradation"
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
            str(item.get("id"))
            for item in sectors
        ]

        affected_airports = [
            str(item.get("id"))
            for item in airports
        ]

        evidence = self.evidence.add(
            kind="DIAGNOSIS",
            title="Initial causal diagnosis",
            summary=alert_text,
            source="mock_engine/state.json",
            severity=(
                "HIGH"
                if affected_sectors
                else "MEDIUM"
            ),
            data={
                "primary_cause": primary_cause,
                "affected_sectors": affected_sectors,
                "affected_airports": affected_airports,
            },
        )

        state.diagnosis = {
            "summary": alert_text,
            "primary_cause": primary_cause,
            "secondary_causes": [
                item.get(
                    "type",
                    "unknown",
                )
                for item in alerts[1:]
            ],
            "affected_flights": [
                state.target_flight_id
            ],
            "affected_sectors": affected_sectors,
            "affected_airports": affected_airports,
            "urgency": (
                "HIGH"
                if world.get(
                    "urgency"
                ) == "HIGH"
                else "MEDIUM"
            ),
            "evidence_ids": [
                evidence.evidence_id
            ],
        }

        state.events.append(
            self._event(
                state,
                "DIAGNOSIS_READY",
                "Causal factors and stressed resources identified.",
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _plan(
        self,
        state: AgentState,
    ) -> None:
        candidates = (
            self.engine.get_alternatives(
                state.target_flight_id
            )
        )

        state.candidates = candidates

        evidence = self.evidence.add(
            kind="CANDIDATE_SET",
            title="Intervention candidates loaded",
            summary=(
                f"Received {len(candidates)} candidate "
                f"interventions for {state.target_flight_id}."
            ),
            source="mock_engine/alternatives.json",
            data={
                "candidate_count": len(candidates)
            },
        )

        state.events.append(
            self._event(
                state,
                "CANDIDATES_READY",
                f"Loaded {len(candidates)} intervention candidates.",
                evidence_ids=[
                    evidence.evidence_id
                ],
            )
        )

    def _evaluate(
        self,
        state: AgentState,
    ) -> None:
        state.feasible_candidates = (
            feasible_candidates(
                state.candidates
            )
        )

        rejected = rejected_candidates(
            state.candidates
        )

        for candidate in rejected:
            candidate_id = str(
                candidate.get(
                    "candidate_id"
                )
            )

            evidence = self.evidence.add(
                kind="CONSTRAINT",
                title=(
                    f"{candidate_id} rejected"
                ),
                summary=(
                    "Candidate failed one or more hard constraints."
                ),
                source="mock_engine/alternatives.json",
                candidate_id=candidate_id,
                severity="HIGH",
                data={
                    "rejection_reasons": (
                        candidate.get(
                            "rejection_reasons",
                            [],
                        )
                    )
                },
            )

            state.events.append(
                self._event(
                    state,
                    "CANDIDATE_REJECTED",
                    (
                        f"Rejected {candidate_id} "
                        "by hard constraint evidence."
                    ),
                    candidate_id=candidate_id,
                    evidence_ids=[
                        evidence.evidence_id
                    ],
                )
            )

        if not state.feasible_candidates:
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
            source="mock_engine/alternatives.json",
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
            str(candidate["candidate_id"])
            for candidate
            in state.feasible_candidates
        ]

        state.simulation_results = (
            self.engine.get_simulation_results(
                candidate_ids
            )
        )

        state.stress_test_results = (
            self.engine.get_stress_results(
                candidate_ids
            )
        )

        evidence = self.evidence.add(
            kind="STRESS_TEST",
            title="Future-state evidence loaded",
            summary=(
                f"Stress-test results loaded for "
                f"{len(candidate_ids)} feasible candidates."
            ),
            source="mock_engine/stress_tests.json",
            data={
                "candidate_ids": candidate_ids
            },
        )

        state.events.append(
            self._event(
                state,
                "STRESS_TEST_READY",
                "Future-state results are available for the critic.",
                evidence_ids=[
                    evidence.evidence_id
                ],
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
                f"Candidate {state.leading_candidate_id} "
                "not found in mock engine."
            )

        result = criticise_candidate(
            candidate,
            stress_result,
        )

        evidence = self.evidence.add(
            kind="CRITIC",
            title="Recommendation challenge",
            summary=result.finding,
            source="mock_engine/stress_tests.json",
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
                "Critic evaluated the preliminary leader.",
                candidate_id=result.candidate_id,
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
                critic_result=state.critic_result,
                evidence_ids=evidence_ids,
            )
        )

        state.recommendation = recommendation

        evidence = self.evidence.add(
            kind="RECOMMENDATION",
            title="Resilient recommendation prepared",
            summary=recommendation.summary,
            source="mock deterministic synthesizer",
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
        candidate_id: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> AgentEvent:
        state.step += 1

        return AgentEvent(
            sequence=state.step,
            stage=state.stage,
            event_type=event_type,
            message=message,
            candidate_id=candidate_id,
            evidence_ids=evidence_ids or [],
        )