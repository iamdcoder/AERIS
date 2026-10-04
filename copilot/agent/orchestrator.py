from typing import Any
from copilot.agent.critic import DecisionCritic
from copilot.agent.synthesizer import DecisionSynthesizer
from .critic import criticise_candidate
from .diagnostics import (
    build_causal_diagnosis,
)
from .evidence import EvidenceStore
from .gemini_runner import (
    GeminiInvestigator,
)
from copilot.agent.approval import ApprovalController
from copilot.agent.reassessment import CandidateReassessor
from .investigation_quality import (
    InvestigationQuality,
)
from copilot.agent.decision_lifecycle import (
    DecisionLifecycleController,
)
from .planner import (
    NoFeasibleCandidateError,
    feasible_candidates,
    select_initial_leader,
)
from .prompts import (
    AERIS_AGENT_SYSTEM_PROMPT,
)
from .state import (
    AgentEvent,
    AgentStage,
    AgentState,
    Diagnosis,
    InvestigationStatus,
    RunStatus,
    can_transition,
    new_agent_state,
    transition,
)
from .synthesizer import (
    build_recommendation,
)
from copilot.engine.client import EngineClient, RealEngineClient
from copilot.tools import (
    ToolRegistry,
    build_default_registry,
)

class AgentOrchestrator:

    def __init__(
        self,
        
        *,
        registry: ToolRegistry | None = None,
        engine: EngineClient | None = None,
        gemini_investigator: GeminiInvestigator | None = None,
    ) -> None:
        self.engine = engine or RealEngineClient()
        self.registry = (
            registry
            or build_default_registry(
                self.engine
            )
        )
        self.critic = DecisionCritic()
        self.synthesizer = DecisionSynthesizer()
        self.gemini_investigator = (
         gemini_investigator
        )
        self.controller = ApprovalController()
        self.reassessor = CandidateReassessor(
            ranker=self.ranker,
        )
        self.decision_lifecycle = (
            DecisionLifecycleController()
        )

        self.evidence = EvidenceStore()

    def run_mock_preview(
        self,
        *,
        run_id: str = "RUN-001",
        scenario_id: str = (
            "mumbai_weather_crisis"
        ),
        target_flight_id: str = "F102",
    ) -> AgentState:
        self.evidence.reset()

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
                    "begin deterministic diagnosis."
                ),
            )

            self._diagnose(
                state
            )

            self._continue_after_diagnosis(
                state
            )

            return state

        except Exception as exc:
            return self._fail_state(
                state,
                exc,
            )
    def _rejected_candidate_ids_for_current_run(
        self,
    ) -> list[str]:
        return [
            record.candidate_id
            for record in self.approval_controller.history
            if record.decision.value == "REJECTED"
        ]
        
    def run_hybrid_preview(
        self,
        *,
        run_id: str = "RUN-HYBRID-001",
        scenario_id: str = (
            "mumbai_weather_crisis"
        ),
        target_flight_id: str = "F102",
        gemini_investigator: GeminiInvestigator | None = None,
    ) -> AgentState:
        """
        Attempt a Gemini-backed investigation.

        If Gemini is unavailable or evidence is insufficient,
        AERIS falls back to deterministic diagnosis rather
        than fabricating a result.

        After diagnosis, both paths use the same downstream
        candidate/evaluation/stress-test/critic pipeline.
        """

        self.evidence.reset()

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
                            "Gemini could not be initialized: "
                            f"{exc}"
                        ),
                    )

                    self._diagnose(
                        state
                    )

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

            if (
                result.status
                == "COMPLETED"
            ):
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

                self._diagnose(
                    state
                )

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
                "Diagnosis complete; "
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
                "Critic complete; "
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

    def _invoke_tool(
        self,
        state: AgentState,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ):
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

        if not result.ok:
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
                    tool_name=(
                        result.tool_name
                    ),
                )
            )

            raise RuntimeError(
                (
                    f"{result.tool_name} failed: "
                    f"{result.error_message}"
                )
            )

        evidence_ids = []

        for item in (
            result.evidence
        ):
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
                tool_name=(
                    result.tool_name
                ),
                evidence_ids=evidence_ids,
            )
        )

        return result, evidence_ids

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

        self._remember(
            state,
            "OBSERVATION",
            (
                "Initial airspace, disruption and "
                "target-flight state loaded."
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
            )
        )

        self._sync_evidence(
            state
        )

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

        state.investigation_plan = (
            plan
        )

        state.events.append(
            self._event(
                state,
                "INVESTIGATION_PLAN_CREATED",
                (
                    f"Deterministic investigation "
                    f"selected {len(plan.questions)} "
                    "question(s)."
                ),
            )
        )

        for question in (
            plan.questions
        ):
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

        state.diagnosis = (
            diagnosis
        )

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

        self._sync_evidence(
            state
        )

    def _record_gemini_result(
        self,
        state: AgentState,
        result: Any,
    ) -> None:
        for call in (
            result.tool_calls
        ):
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
                            f"Gemini requested "
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
                        evidence[
                            "summary"
                        ],
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

        investigation_results = (
            result.investigation_results
        )

        diagnosis = (
            build_causal_diagnosis(
                world_state=(
                    world_state
                ),
                investigation_results=(
                    investigation_results
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
        feasible = []

        for candidate in (
            state.candidates
        ):
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

            if (
                result.data.get(
                    "feasible"
                )
                is True
            ):
                candidate.update(result.data)
                feasible.append(
                    candidate
                )
            else:
                candidate.update(result.data)
                state.events.append(
                    self._event(
                        state,
                        "CANDIDATE_REJECTED",
                        (
                            f"{candidate_id} rejected "
                            "by deterministic hard constraints."
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

        state.leading_candidate_id = (
            str(
                leader[
                    "candidate_id"
                ]
            )
        )

        evidence = self.evidence.add(
            kind=(
                "PRELIMINARY_SELECTION"
            ),
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

        for candidate_id in (
            candidate_ids
        ):
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

        ranked, ranking_evidence_ids = self._invoke_tool(
            state,
            "score_candidates",
            {"candidate_ids": candidate_ids},
        )
        scored_candidates = ranked.data.get("candidates", [])
        if scored_candidates:
            scored_by_id = {
                candidate["candidate_id"]: candidate
                for candidate in scored_candidates
            }
            state.candidates = [
                {**candidate, **scored_by_id.get(candidate.get("candidate_id"), {})}
                for candidate in state.candidates
            ]
            state.feasible_candidates = sorted(
                [candidate for candidate in state.candidates if candidate.get("feasible") is True],
                key=lambda candidate: candidate.get("decision_score", 0.0),
                reverse=True,
            )
            if state.feasible_candidates:
                state.events.append(
                    self._event(
                        state,
                        "ENGINE_RANKING_READY",
                        f"The deterministic engine ranked {len(state.feasible_candidates)} feasible candidate(s).",
                        candidate_id=state.feasible_candidates[0]["candidate_id"],
                        evidence_ids=ranking_evidence_ids,
                    )
                )

        state.events.append(
            self._event(
                state,
                "EVALUATION_COMPLETE",
                (
                    f"Network simulation and stress "
                    f"testing completed for "
                    f"{len(candidate_ids)} candidate(s)."
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
                for item
                in state.candidates
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
                for item
                in state.stress_test_results
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

        result = (
            criticise_candidate(
                candidate,
                stress_result,
            )
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
            evidence_ids=(
                evidence_ids or []
            ),
            data=data or {},
        )