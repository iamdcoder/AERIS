from __future__ import annotations

from typing import Any

from copilot.agent.approval import ApprovalController
from copilot.agent.critic import (
    CriticResult as DecisionCriticResult,
    DecisionCritic,
)
from copilot.agent.decision_lifecycle import (
    DecisionLifecycleController,
)
from copilot.agent.diagnostics import (
    build_causal_diagnosis,
)
from copilot.agent.evidence import (
    EvidenceStore,
)
from copilot.agent.gemini_runner import (
    GeminiInvestigator,
)
from copilot.agent.planner import (
    InterventionPlanner,
    NoFeasibleCandidateError,
    select_initial_leader,
)
from copilot.agent.ranker import (
    DecisionRanker,
    RankingSummary,
)
from copilot.agent.reassessment import (
    CandidateReassessor,
)
from copilot.agent.scoring import (
    DecisionScoreResult,
)
from copilot.agent.state import (
    AgentEvent,
    AgentStage,
    AgentState,
    ApprovalState,
    CriticResult as StateCriticResult,
    InvestigationStatus,
    Recommendation,
    RunStatus,
    can_transition,
    new_agent_state,
    transition,
)
from copilot.agent.synthesizer import (
    DecisionSynthesizer,
)
from copilot.engine.client import (
    EngineClient,
    RealEngineClient,
)
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)


class AgentOrchestrator:
    """
    Main AERIS agent orchestration layer.

    Responsibilities:

    OBSERVE
        ↓
    DIAGNOSE
        ↓
    PLAN
        ↓
    EVALUATE
        ↓
    STRESS TEST
        ↓
    CRITIC
        ↓
    RECOMMEND
        ↓
    HUMAN APPROVAL

    Post-approval lifecycle is handled through
    DecisionLifecycleController.

    The orchestrator never replaces deterministic aviation
    calculations with model-generated numbers.
    """

    def __init__(
        self,
        *,
        registry: ToolRegistry | None = None,
        engine: EngineClient | None = None,
        engine_client: EngineClient | None = None,
        gemini_investigator: GeminiInvestigator | None = None,
    ) -> None:
        if (
            engine is not None
            and engine_client is not None
            and engine is not engine_client
        ):
            raise ValueError(
                "Provide either 'engine' or 'engine_client', "
                "not two different clients."
            )

        selected_engine = (
            engine
            or engine_client
            or RealEngineClient()
        )

        self.engine = selected_engine

        self.registry = (
            registry
            or build_default_registry(
                self.engine
            )
        )

        self.planner = (
            InterventionPlanner()
        )

        self.ranker = (
            DecisionRanker()
        )

        self.critic = (
            DecisionCritic()
        )

        self.synthesizer = (
            DecisionSynthesizer()
        )

        self.gemini_investigator = (
            gemini_investigator
        )

        self.approval_controller = (
            ApprovalController()
        )

        # Backward-compatible alias.
        self.controller = (
            self.approval_controller
        )

        self.reassessor = (
            CandidateReassessor(
                ranker=self.ranker
            )
        )

        self.decision_lifecycle = (
            DecisionLifecycleController(
                reassessor=self.reassessor,
                engine=self.engine,
            )
        )

        self.evidence = (
            EvidenceStore()
        )

        self._score_result: (
            DecisionScoreResult | None
        ) = None

        self._ranking_summary: (
            RankingSummary | None
        ) = None

        self._decision_critic_result: (
            DecisionCriticResult | None
        ) = None

        self._active_state: (
            AgentState | None
        ) = None

    def _reset_run(
        self,
        state: AgentState,
    ) -> None:
        self.evidence.reset()

        self.approval_controller = (
            ApprovalController()
        )

        self.controller = (
            self.approval_controller
        )

        self._score_result = None
        self._ranking_summary = None
        self._decision_critic_result = None
        self._active_state = state

    def run_mock_preview(
        self,
        *,
        run_id: str = "RUN-001",
        scenario_id: str = (
            "mumbai_weather_crisis"
        ),
        target_flight_id: str = "F102",
    ) -> AgentState:
        state = new_agent_state(
            run_id,
            scenario_id,
            target_flight_id,
        )

        self._reset_run(state)

        try:
            self._observe(state)

            transition(
                state,
                AgentStage.DIAGNOSE,
                (
                    "Observation complete; "
                    "begin deterministic diagnosis."
                ),
            )

            self._diagnose(state)

            self._continue_after_diagnosis(
                state
            )

            return state

        except Exception as exc:
            return self._fail_state(
                state,
                exc,
            )

    def run_hybrid_preview(
        self,
        *,
        run_id: str = (
            "RUN-HYBRID-001"
        ),
        scenario_id: str = (
            "mumbai_weather_crisis"
        ),
        target_flight_id: str = "F102",
        gemini_investigator: (
            GeminiInvestigator | None
        ) = None,
    ) -> AgentState:
        state = new_agent_state(
            run_id,
            scenario_id,
            target_flight_id,
        )

        self._reset_run(state)

        try:
            self._observe(state)

            transition(
                state,
                AgentStage.DIAGNOSE,
                (
                    "Observation complete; "
                    "attempt hybrid investigation."
                ),
            )

            investigator = (
                gemini_investigator
                or self.gemini_investigator
            )

            if investigator is None:
                try:
                    investigator = (
                        GeminiInvestigator(
                            registry=self.registry
                        )
                    )
                except Exception as exc:
                    self._record_fallback(
                        state,
                        (
                            "Gemini could not be "
                            f"initialized: {exc}"
                        ),
                    )

                    self._diagnose(state)

                    self._continue_after_diagnosis(
                        state
                    )

                    return state

            result = (
                investigator.investigate(
                    target_flight_id=(
                        target_flight_id
                    ),
                    scenario_id=scenario_id,
                    initial_state=(
                        state.world_state
                    ),
                )
            )

            self._record_gemini_result(
                state,
                result,
            )

            if result.status == "COMPLETED":
                self._apply_gemini_diagnosis(
                    state,
                    result,
                )
            else:
                self._record_fallback(
                    state,
                    (
                        "Gemini investigation did not "
                        "produce sufficient evidence. "
                        "Deterministic investigation is "
                        "being used as fallback."
                    ),
                )

                self._diagnose(state)

            self._continue_after_diagnosis(
                state
            )

            return state

        except Exception as exc:
            return self._fail_state(
                state,
                exc,
            )

    def _continue_after_diagnosis(
        self,
        state: AgentState,
    ) -> None:
        transition(
            state,
            AgentStage.PLAN,
            (
                "Diagnosis complete; select intervention "
                "families and generate candidates."
            ),
        )

        self._plan(state)

        transition(
            state,
            AgentStage.EVALUATE,
            (
                "Candidate set loaded; evaluate "
                "hard feasibility."
            ),
        )

        self._evaluate(state)

        transition(
            state,
            AgentStage.STRESS_TEST,
            (
                "Feasible candidates isolated; "
                "simulate and stress-test them."
            ),
        )

        self._stress_test(state)

        transition(
            state,
            AgentStage.CRITIC,
            (
                "Evidence collected; challenge "
                "the preliminary leader."
            ),
        )

        self._critic(state)

        transition(
            state,
            AgentStage.RECOMMEND,
            (
                "Critic complete; synthesize "
                "recommendation."
            ),
        )

        self._recommend(state)

        transition(
            state,
            AgentStage.HUMAN_APPROVAL,
            (
                "Recommendation prepared; "
                "waiting for human approval."
            ),
        )

        self._request_human_approval(
            state
        )

        state.status = (
            RunStatus.WAITING_HUMAN
        )

        self._sync_evidence(state)

    def _invoke_tool(
        self,
        state: AgentState,
        tool_name: str,
        arguments: (
            dict[str, Any] | None
        ) = None,
    ):
        state.events.append(
            self._event(
                state,
                "TOOL_CALL",
                (
                    f"Calling tool "
                    f"{tool_name}."
                ),
                tool_name=tool_name,
            )
        )

        result = self.registry.invoke(
            tool_name,
            arguments or {},
        )

        if not result.ok:
            message = (
                f"{result.tool_name}: "
                f"{result.error_message}"
            )

            state.errors.append(
                message
            )

            state.events.append(
                self._event(
                    state,
                    "TOOL_ERROR",
                    result.summary,
                    tool_name=(
                        result.tool_name
                    ),
                )
            )

            raise RuntimeError(
                (
                    f"{result.tool_name} "
                    f"failed: "
                    f"{result.error_message}"
                )
            )

        evidence_ids: list[str] = []

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
                source=(
                    result.tool_name
                ),
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
                tool_name=(
                    result.tool_name
                ),
                evidence_ids=evidence_ids,
            )
        )

        return (
            result,
            evidence_ids,
        )

    def _observe(
        self,
        state: AgentState,
    ) -> None:
        airspace, airspace_evidence = (
            self._invoke_tool(
                state,
                "get_airspace_state",
            )
        )

        disruptions, disruption_evidence = (
            self._invoke_tool(
                state,
                "get_disruptions",
            )
        )

        target, target_evidence = (
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

        target_data = (
            target.data or {}
        )

        disruption_data = (
            disruptions.data or {}
        )

        state.world_state = {
            **(
                airspace.data
                or {}
            ),
            "disruptions": (
                disruption_data
            ),
            "alerts": (
                disruption_data.get(
                    "disruptions",
                    [],
                )
            ),
            "target": target_data,
            "target_flight": (
                target_data
            ),
            "target_flight_id": (
                state.target_flight_id
            ),
        }

        self._remember(
            state,
            "OBSERVATION",
            (
                "Initial airspace, disruption "
                "and target-flight state loaded."
            ),
            "deterministic_observation",
            "HIGH",
        )

        state.events.append(
            self._event(
                state,
                "OBSERVATION_READY",
                (
                    "Airspace, disruption and "
                    "target-flight state assembled."
                ),
                evidence_ids=[
                    *airspace_evidence,
                    *disruption_evidence,
                    *target_evidence,
                ],
            )
        )

        self._sync_evidence(state)

    def _diagnose(
        self,
        state: AgentState,
    ) -> None:
        from .investigation import (
            build_investigation_plan,
            update_plan_completeness,
        )

        plan = (
            build_investigation_plan(
                state.world_state
            )
        )

        state.investigation_plan = plan

        state.events.append(
            self._event(
                state,
                "INVESTIGATION_PLAN_CREATED",
                (
                    "Deterministic investigation "
                    f"selected {len(plan.questions)} "
                    "question(s)."
                ),
            )
        )

        for question in plan.questions:
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

        update_plan_completeness(
            plan
        )

        state.investigation_plan = plan

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

        self._remember(
            state,
            "DIAGNOSIS",
            diagnosis.summary,
            "deterministic_diagnosis",
            "HIGH",
        )

        state.events.append(
            self._event(
                state,
                "DIAGNOSIS_READY",
                diagnosis.summary,
                evidence_ids=(
                    diagnosis.evidence_ids
                ),
            )
        )

        self._sync_evidence(state)

    def _plan(
        self,
        state: AgentState,
    ) -> None:
        intervention_plan = (
            self.planner.plan(
                state.world_state,
                state.diagnosis,
            )
        )

        state.events.append(
            self._event(
                state,
                "INTERVENTION_PLAN_READY",
                intervention_plan.rationale,
                data=(
                    intervention_plan.to_agent_context()
                ),
            )
        )

        if not intervention_plan.generate_candidates:
            raise NoFeasibleCandidateError(
                (
                    "No intervention trigger is active; "
                    "no candidates should be generated."
                )
            )

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

        candidates = list(
            (
                result.data or {}
            ).get(
                "alternatives",
                [],
            )
        )

        state.candidates = (
            candidates
        )

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
        feasible: list[
            dict[str, Any]
        ] = []

        for candidate in (
            state.candidates
        ):
            candidate_id = str(
                candidate.get(
                    "candidate_id",
                    "",
                )
            )

            if not candidate_id:
                continue

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

            candidate.update(
                result.data or {}
            )

            if (
                result.data
                and result.data.get(
                    "feasible"
                )
                is True
            ):
                feasible.append(
                    candidate
                )
            else:
                state.events.append(
                    self._event(
                        state,
                        "CANDIDATE_REJECTED",
                        (
                            f"{candidate_id} "
                            "rejected by deterministic "
                            "hard constraints."
                        ),
                        candidate_id=(
                            candidate_id
                        ),
                        evidence_ids=evidence_ids,
                        data={
                            "rejection_reasons": (
                                candidate.get(
                                    "rejection_reasons",
                                    [],
                                )
                            )
                        },
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

        leader = (
            select_initial_leader(
                state.candidates
            )
        )

        state.leading_candidate_id = str(
            leader["candidate_id"]
        )

        evidence = self.evidence.add(
            kind="PRELIMINARY_SELECTION",
            title=(
                "Preliminary leader selected"
            ),
            summary=(
                f"{state.leading_candidate_id} "
                "leads on immediate/local criteria."
            ),
            source="deterministic planner",
            candidate_id=(
                state.leading_candidate_id
            ),
            data={
                "local_score": (
                    leader.get(
                        "local_score"
                    )
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

        simulations: list[
            dict[str, Any]
        ] = []

        stress_results: list[
            dict[str, Any]
        ] = []

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
                simulation.data or {}
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
                stress.data or {}
            )

        state.simulation_results = (
            simulations
        )

        state.stress_test_results = (
            stress_results
        )

        score_result, ranking = (
            self.ranker.rank(
                candidates=(
                    state.candidates
                ),
                simulations=(
                    simulations
                ),
                stress_tests=(
                    stress_results
                ),
            )
        )

        self._score_result = (
            score_result
        )

        self._ranking_summary = (
            ranking
        )

        score_map = {
            item.candidate_id: item
            for item in score_result.scores
        }

        merged_candidates = []

        for candidate in state.candidates:
            candidate_id = str(
                candidate.get(
                    "candidate_id",
                    "",
                )
            )

            score = score_map.get(
                candidate_id
            )

            if score is None:
                merged_candidates.append(
                    candidate
                )
                continue

            updated = dict(
                candidate
            )

            updated.update(
                {
                    "decision_score": (
                        score.score
                    ),
                    "decision_regret": (
                        score.decision_regret
                    ),
                    "local_regret": (
                        score.local_regret
                    ),
                    "score_components": (
                        score.components.model_dump()
                    ),
                    "second_intervention_probability": (
                        score.second_intervention_probability
                    ),
                    "score_explanation": (
                        score.explanation
                    ),
                }
            )

            merged_candidates.append(
                updated
            )

        state.candidates = (
            merged_candidates
        )

        state.feasible_candidates = [
            candidate
            for candidate
            in merged_candidates
            if (
                candidate.get(
                    "feasible"
                )
                is True
            )
        ]

        state.events.append(
            self._event(
                state,
                "ENGINE_RANKING_READY",
                (
                    f"Deterministic scorer ranked "
                    f"{len(score_result.scores)} "
                    "candidate(s); network-level leader "
                    f"is {ranking.recommended_candidate_id or 'NONE'}."
                ),
                candidate_id=(
                    ranking.recommended_candidate_id
                ),
                data={
                    "score_gap": (
                        ranking.score_gap
                    ),
                    "local_vs_global_flip": (
                        ranking.local_vs_global_flip
                    ),
                    "ranked_candidate_ids": (
                        score_result.ranked_candidate_ids
                    ),
                },
            )
        )

        state.events.append(
            self._event(
                state,
                "EVALUATION_COMPLETE",
                (
                    "Network simulation and stress testing "
                    f"completed for {len(candidate_ids)} "
                    "candidate(s)."
                ),
            )
        )

    def _critic(
        self,
        state: AgentState,
    ) -> None:
        if (
            self._score_result is None
            or self._ranking_summary is None
        ):
            raise RuntimeError(
                "Ranking evidence is unavailable "
                "for critic evaluation."
            )

        leader_id = (
            state.leading_candidate_id
        )

        leader_score = next(
            (
                item
                for item
                in self._score_result.scores
                if item.candidate_id
                == leader_id
            ),
            None,
        )

        if leader_score is None:
            raise RuntimeError(
                (
                    f"Preliminary leader "
                    f"{leader_id!r} has no "
                    "decision score."
                )
            )

        stress_result = next(
            (
                item
                for item
                in state.stress_test_results
                if item.get(
                    "candidate_id"
                )
                == leader_id
            ),
            None,
        )

        simulation = next(
            (
                item
                for item
                in state.simulation_results
                if item.get(
                    "candidate_id"
                )
                == leader_id
            ),
            None,
        )

        result = self.critic.review(
            leader=leader_score,
            ranking=(
                self._ranking_summary
            ),
            stress_test=stress_result,
            simulation=simulation,
        )

        self._decision_critic_result = (
            result
        )

        state.critic_result = (
            StateCriticResult(
                candidate_id=(
                    result.candidate_id
                ),
                challenged=(
                    result.challenged
                ),
                finding=(
                    result.summary
                ),
                trigger_conditions=[
                    finding.condition
                    for finding
                    in result.findings
                ],
                evidence_ids=[],
            )
        )

        evidence = self.evidence.add(
            kind="CRITIC",
            title=(
                "Recommendation challenge"
            ),
            summary=result.summary,
            source="deterministic critic",
            candidate_id=(
                result.candidate_id
            ),
            severity=(
                result.challenge_severity
            ),
            data=result.model_dump(),
        )

        state.critic_result.evidence_ids = [
            evidence.evidence_id
        ]

        state.events.append(
            self._event(
                state,
                "CRITIC_COMPLETE",
                result.summary,
                candidate_id=(
                    result.candidate_id
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
                data={
                    "challenged": (
                        result.challenged
                    ),
                    "replacement_candidate_id": (
                        result.replacement_candidate_id
                    ),
                },
            )
        )

    def _recommend(
        self,
        state: AgentState,
    ) -> None:
        if (
            self._score_result is None
            or self._ranking_summary is None
        ):
            raise RuntimeError(
                "Decision ranking is unavailable "
                "for recommendation synthesis."
            )

        if (
            self._decision_critic_result
            is None
        ):
            raise RuntimeError(
                "Decision critic result is unavailable "
                "for recommendation synthesis."
            )

        final = (
            self.synthesizer.synthesize(
                ranking=(
                    self._ranking_summary
                ),
                score_result=(
                    self._score_result
                ),
                critic_result=(
                    self._decision_critic_result
                ),
                target_flight_id=(
                    state.target_flight_id
                ),
            )
        )

        if final.candidate_id is None:
            raise NoFeasibleCandidateError(
                (
                    "No safe candidate survived "
                    "ranking and critic review."
                )
            )

        rejected = [
            candidate
            for candidate
            in state.candidates
            if (
                candidate.get(
                    "feasible"
                )
                is not True
            )
        ]

        state.recommendation = (
            Recommendation(
                candidate_id=(
                    final.candidate_id
                ),
                confidence=(
                    final.confidence
                ),
                summary=(
                    final.explanation
                ),
                why_selected=[
                    item.statement
                    for item
                    in final.evidence[:6]
                ],
                rejected_candidates=(
                    rejected
                ),
                critic=(
                    state.critic_result
                ),
                evidence_ids=(
                    self.evidence.ids()
                ),
                human_approval_required=True,
            )
        )

        state.leading_candidate_id = (
            final.candidate_id
        )

        evidence = self.evidence.add(
            kind="RECOMMENDATION",
            title=(
                "Resilient recommendation prepared"
            ),
            summary=(
                final.explanation
            ),
            source=(
                "deterministic synthesizer"
            ),
            candidate_id=(
                final.candidate_id
            ),
            data={
                "confidence": (
                    final.confidence
                ),
                "network_level_winner": (
                    self._ranking_summary
                    .recommended_candidate_id
                ),
                "critic_replacement": (
                    self._decision_critic_result
                    .replacement_candidate_id
                ),
                "local_vs_global_flip": (
                    self._ranking_summary
                    .local_vs_global_flip
                ),
            },
        )

        state.recommendation.evidence_ids = [
            evidence.evidence_id
        ]

        state.events.append(
            self._event(
                state,
                "RECOMMENDATION_READY",
                (
                    f"Recommendation prepared: "
                    f"{final.candidate_id}."
                ),
                candidate_id=(
                    final.candidate_id
                ),
                evidence_ids=[
                    evidence.evidence_id
                ],
                data={
                    "confidence": (
                        final.confidence
                    ),
                    "requires_human_approval": (
                        final.requires_human_approval
                    ),
                    "local_vs_global_flip": (
                        final.local_vs_global_flip
                    ),
                },
            )
        )

    def _request_human_approval(
        self,
        state: AgentState,
    ) -> None:
        if (
            state.recommendation is None
            or state.recommendation.candidate_id
            is None
        ):
            raise RuntimeError(
                "Cannot request approval without "
                "a recommendation."
            )

        recommendation_id = (
            f"{state.run_id}:REC:"
            f"{state.step + 1:03d}"
        )

        request = (
            self.approval_controller.request(
                recommendation_id=(
                    recommendation_id
                ),
                candidate_id=(
                    state.recommendation
                    .candidate_id
                ),
                target_flight_id=(
                    state.target_flight_id
                ),
                explanation=(
                    state.recommendation.summary
                ),
            )
        )

        state.approval = (
            ApprovalState(
                required=True,
                status="AWAITING_APPROVAL",
                decision="PENDING",
                reason=None,
            )
        )

        state.events.append(
            self._event(
                state,
                "HUMAN_APPROVAL_REQUIRED",
                (
                    "Human approval required for "
                    f"{request.candidate_id}."
                ),
                candidate_id=(
                    request.candidate_id
                ),
                data={
                    "recommendation_id": (
                        request.recommendation_id
                    ),
                    "requested_by": (
                        request.requested_by
                    ),
                },
            )
        )

    def approve_current_recommendation(
        self,
        *,
        decided_by: str = (
            "human_dispatcher"
        ),
    ) -> AgentState:
        if self._active_state is None:
            raise RuntimeError(
                "No active AERIS run exists."
            )

        state = self._active_state

        record = (
            self.approval_controller.approve(
                decided_by=decided_by
            )
        )

        state.approval.status = (
            record.decision.value
        )

        state.approval.decision = (
            record.decision.value
        )

        state.approval.reason = None

        candidate = (
            self._find_candidate(
                state,
                record.candidate_id,
            )
        )

        simulation = (
            self._find_simulation(
                state,
                record.candidate_id,
            )
        )

        if candidate is None:
            return self._fail_state(
                state,
                RuntimeError(
                    (
                        f"Approved candidate "
                        f"{record.candidate_id!r} "
                        "was not found."
                    )
                ),
            )

        transition(
            state,
            AgentStage.EXECUTE,
            (
                "Human approval recorded; "
                "execute approved intervention."
            ),
        )

        lifecycle = (
            self.decision_lifecycle.process_approval(
                approval_record=record,
                target_flight_id=(
                    state.target_flight_id
                ),
                candidate=candidate,
                registry=self.registry,
                simulation=simulation,
            )
        )

        if (
            lifecycle.execution
            is not None
        ):
            state.events.append(
                self._event(
                    state,
                    "EXECUTION_RESULT",
                    (
                        lifecycle.execution.summary
                    ),
                    candidate_id=(
                        lifecycle.execution.candidate_id
                    ),
                    data=(
                        lifecycle.execution
                        .model_dump()
                    ),
                )
            )

        if (
            lifecycle.execution
            is not None
            and lifecycle.execution.status.value
            == "EXECUTED"
        ):
            transition(
                state,
                AgentStage.VERIFY,
                (
                    "Approved intervention executed; "
                    "verify resulting network state."
                ),
            )

        if lifecycle.verification is not None:
            state.verification_result = (
                lifecycle.verification.model_dump()
            )

            state.events.append(
                self._event(
                    state,
                    "VERIFICATION_RESULT",
                    (
                        lifecycle.verification.summary
                    ),
                    candidate_id=(
                        lifecycle.verification.candidate_id
                    ),
                    data=(
                        lifecycle.verification
                        .model_dump()
                    ),
                )
            )

            if (
                lifecycle.verification.status.value
                == "VERIFIED"
            ):
                transition(
                    state,
                    AgentStage.COMPLETE,
                    (
                        "Post-intervention verification "
                        "passed."
                    ),
                )

                state.status = (
                    RunStatus.COMPLETED
                )

            elif (
                lifecycle.verification.status.value
                == "REASSESSMENT_REQUIRED"
            ):
                transition(
                    state,
                    AgentStage.REASSESS,
                    (
                        "Verification detected degradation; "
                        "reassessment required."
                    ),
                )

                state.status = (
                    RunStatus.WAITING_HUMAN
                )

            else:
                transition(
                    state,
                    AgentStage.FAILED,
                    (
                        "Post-intervention verification "
                        "failed."
                    ),
                )

                state.status = (
                    RunStatus.FAILED
                )

        else:
            if can_transition(
                state.stage,
                AgentStage.DEGRADED,
            ):
                transition(
                    state,
                    AgentStage.DEGRADED,
                    lifecycle.summary,
                )

            state.status = (
                RunStatus.DEGRADED
            )

        self._sync_evidence(state)

        return state

    def reject_current_recommendation(
        self,
        reason: str,
        *,
        decided_by: str = (
            "human_dispatcher"
        ),
    ) -> AgentState:
        if self._active_state is None:
            raise RuntimeError(
                "No active AERIS run exists."
            )

        state = self._active_state

        record = (
            self.approval_controller.reject(
                reason=reason,
                decided_by=decided_by,
            )
        )

        state.approval.status = (
            record.decision.value
        )

        state.approval.decision = (
            record.decision.value
        )

        state.approval.reason = (
            record.reason
        )

        transition(
            state,
            AgentStage.REASSESS,
            (
                "Human rejected the recommendation; "
                "reassess remaining candidates."
            ),
        )

        previous_rejected = [
            item.candidate_id
            for item
            in self.approval_controller.history
            if (
                item.decision.value
                == "REJECTED"
            )
        ]

        lifecycle = (
            self.decision_lifecycle.process_rejection(
                approval_record=record,
                candidates=state.candidates,
                simulations=state.simulation_results,
                stress_tests=state.stress_test_results,
                previously_rejected_ids=(
                    previous_rejected[:-1]
                ),
            )
        )

        state.events.append(
            self._event(
                state,
                "REASSESSMENT_COMPLETE",
                lifecycle.summary,
                candidate_id=(
                    lifecycle.reassessment
                    .new_recommended_candidate_id
                    if lifecycle.reassessment
                    else None
                ),
                data=(
                    lifecycle.reassessment.model_dump()
                    if lifecycle.reassessment
                    else {}
                ),
            )
        )

        if (
            lifecycle.reassessment is None
            or lifecycle.reassessment
            .new_recommended_candidate_id
            is None
        ):
            state.status = (
                RunStatus.COMPLETED
            )
            return state

        new_id = (
            lifecycle.reassessment
            .new_recommended_candidate_id
        )

        state.leading_candidate_id = (
            new_id
        )

        new_candidate = (
            self._find_candidate(
                state,
                new_id,
            )
        )

        if new_candidate is not None:
            # Preserve the new candidate as the visible recommendation.
            state.recommendation = (
                Recommendation(
                    candidate_id=new_id,
                    confidence=0.0,
                    summary=(
                        lifecycle.summary
                    ),
                    why_selected=[],
                    rejected_candidates=[],
                    critic=None,
                    evidence_ids=(
                        self.evidence.ids()
                    ),
                    human_approval_required=True,
                )
            )

        self.approval_controller.reset_for_reassessment()

        self._request_human_approval(
            state
        )

        state.stage = (
            AgentStage.HUMAN_APPROVAL
        )

        state.status = (
            RunStatus.WAITING_HUMAN
        )

        self._sync_evidence(state)

        return state

    def _record_gemini_result(
        self,
        state: AgentState,
        result: Any,
    ) -> None:
        for call in result.tool_calls:
            state.events.append(
                self._event(
                    state,
                    (
                        "GEMINI_TOOL_RESULT"
                        if call.ok
                        else "GEMINI_TOOL_ERROR"
                    ),
                    (
                        call.result_summary
                        or (
                            "Gemini requested "
                            f"{call.name}"
                        )
                    ),
                    tool_name=call.name,
                    data={
                        "arguments": (
                            call.arguments
                        ),
                        "ok": call.ok,
                        "error_code": (
                            call.error_code
                        ),
                    },
                )
            )

        for memory in (
            result.working_memory
        ):
            self._add_memory_record(
                state,
                memory,
            )

        for evidence in (
            result.evidence
        ):
            evidence_id = (
                self._copy_gemini_evidence(
                    evidence
                )
            )

            if evidence_id:
                state.events.append(
                    self._event(
                        state,
                        "EVIDENCE_ADDED",
                        evidence.get(
                            "summary",
                            "Gemini evidence added.",
                        ),
                        evidence_ids=[
                            evidence_id
                        ],
                    )
                )

        state.investigation_results.extend(
            result.investigation_results
        )

        if (
            result.investigation_plan
            is not None
        ):
            state.investigation_plan = (
                result.investigation_plan
            )

    def _apply_gemini_diagnosis(
        self,
        state: AgentState,
        result: Any,
    ) -> None:
        world_state = (
            result.world_state
            or state.world_state
        )

        state.world_state = (
            world_state
        )

        diagnosis = (
            build_causal_diagnosis(
                world_state=world_state,
                investigation_results=(
                    result.investigation_results
                ),
                target_flight_id=(
                    state.target_flight_id
                ),
                evidence_ids=(
                    self.evidence.ids()
                ),
                evidence_completeness=(
                    result.quality.score
                ),
            )
        )

        state.diagnosis = (
            diagnosis
        )

        self._remember(
            state,
            "GEMINI_DIAGNOSIS",
            diagnosis.summary,
            "gemini_hybrid_investigation",
            "HIGH",
        )

        state.events.append(
            self._event(
                state,
                "GEMINI_INVESTIGATION_COMPLETE",
                (
                    "Gemini investigation produced "
                    "sufficient evidence for diagnosis."
                ),
                data={
                    "quality_score": (
                        result.quality.score
                    ),
                    "tool_calls": len(
                        result.tool_calls
                    ),
                    "evidence_count": len(
                        result.evidence
                    ),
                },
            )
        )

    def _record_fallback(
        self,
        state: AgentState,
        message: str,
    ) -> None:
        state.events.append(
            self._event(
                state,
                "AGENT_FALLBACK",
                message,
            )
        )

        self._remember(
            state,
            "FALLBACK",
            message,
            "aeris_runtime",
            "HIGH",
        )

    def _remember(
        self,
        state: AgentState,
        category: str,
        content: str,
        source: str,
        importance: str = "MEDIUM",
    ) -> None:
        self._add_memory_record(
            state,
            {
                "memory_id": (
                    f"M{len(state.working_memory) + 1:03d}"
                ),
                "category": category,
                "content": content,
                "source": source,
                "importance": importance,
                "data": {},
            },
        )

    @staticmethod
    def _add_memory_record(
        state: AgentState,
        memory: dict[str, Any],
    ) -> None:
        state.working_memory.append(
            memory
        )

    def _copy_gemini_evidence(
        self,
        evidence: dict[str, Any],
    ) -> str | None:
        summary = evidence.get(
            "summary"
        )

        if not summary:
            return None

        item = self.evidence.add(
            kind=str(
                evidence.get(
                    "kind",
                    "GEMINI_EVIDENCE",
                )
            ),
            title=str(
                evidence.get(
                    "title",
                    "Gemini tool evidence",
                )
            ),
            summary=str(
                summary
            ),
            source=str(
                evidence.get(
                    "source",
                    "gemini",
                )
            ),
            candidate_id=evidence.get(
                "candidate_id"
            ),
            severity=evidence.get(
                "severity"
            ),
            data=evidence.get(
                "data",
                {},
            ),
        )

        return item.evidence_id

    def _sync_evidence(
        self,
        state: AgentState,
    ) -> None:
        state.evidence = (
            self.evidence.as_dicts()
        )

    def _fail_state(
        self,
        state: AgentState,
        exc: Exception,
    ) -> AgentState:
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

    @staticmethod
    def _find_candidate(
        state: AgentState,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                candidate
                for candidate
                in state.candidates
                if candidate.get(
                    "candidate_id"
                )
                == candidate_id
            ),
            None,
        )

    @staticmethod
    def _find_simulation(
        state: AgentState,
        candidate_id: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item
                in state.simulation_results
                if item.get(
                    "candidate_id"
                )
                == candidate_id
            ),
            None,
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
        return AgentEvent(
            sequence=(
                state.step
                + len(state.events)
                + 1
            ),
            stage=state.stage,
            event_type=event_type,
            message=message,
            tool_name=tool_name,
            candidate_id=candidate_id,
            evidence_ids=(
                evidence_ids or []
            ),
            data=data or {},
        )