from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence

from pydantic import BaseModel, Field


class NoFeasibleCandidateError(RuntimeError):
    """
    Raised when no candidate satisfies the current hard constraints.
    """

    pass


class InterventionType(str, Enum):
    REROUTE = "REROUTE"
    ALTITUDE_SPEED = "ALTITUDE_SPEED"
    TIMING_HOLD = "TIMING_HOLD"
    ALTERNATE_DIVERSION = "ALTERNATE_DIVERSION"
    MONITOR = "MONITOR"


class InterventionIntent(BaseModel):
    intervention_type: InterventionType
    priority: int = Field(ge=0, le=100)
    rationale: str
    required_tools: List[str] = Field(default_factory=list)
    candidate_generation: bool = True


class InterventionPlan(BaseModel):
    scenario_id: str
    target_flight_id: str
    primary_intervention: InterventionType
    intervention_intents: List[InterventionIntent] = Field(
        default_factory=list
    )
    candidate_budget: int = Field(
        default=5,
        ge=1,
        le=5,
    )
    generate_candidates: bool = True
    rationale: str
    evidence_signals: List[str] = Field(default_factory=list)
    fallback_intervention: InterventionType = (
        InterventionType.MONITOR
    )

    def candidate_types(self) -> List[str]:
        return [
            intent.intervention_type.value
            for intent in self.intervention_intents
            if (
                intent.candidate_generation
                and intent.intervention_type
                != InterventionType.MONITOR
            )
        ]

    def required_tools(self) -> List[str]:
        ordered: List[str] = []

        for intent in self.intervention_intents:
            if not intent.candidate_generation:
                continue

            for tool in intent.required_tools:
                if tool not in ordered:
                    ordered.append(tool)

        return ordered

    def to_tool_request(self) -> Dict[str, Any]:
        return {
            "tool_name": "generate_alternatives",
            "arguments": {
                "flight_id": self.target_flight_id,
                "intervention_types": self.candidate_types(),
                "max_candidates": self.candidate_budget,
            },
        }

    def to_agent_context(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "target_flight_id": self.target_flight_id,
            "primary_intervention": (
                self.primary_intervention.value
            ),
            "candidate_intervention_types": (
                self.candidate_types()
            ),
            "candidate_budget": self.candidate_budget,
            "required_tools": self.required_tools(),
            "fallback_intervention": (
                self.fallback_intervention.value
            ),
            "rationale": self.rationale,
            "evidence_signals": list(
                self.evidence_signals
            ),
        }


class PlannerSignals(BaseModel):
    severe_weather: bool = False
    significant_weather: bool = False
    degraded_airport: bool = False
    stressed_sector: bool = False
    target_degraded: bool = False
    active_holding: bool = False
    high_urgency: bool = False
    low_fuel_margin: bool = False
    critical_fuel_margin: bool = False
    disruption_present: bool = False


def feasible_candidates(
    candidates: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Return only candidates that explicitly satisfy hard constraints.

    This helper is intentionally conservative:
    anything that is not explicitly marked feasible=True is excluded.
    """
    feasible: List[Dict[str, Any]] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        if candidate.get("feasible") is True:
            feasible.append(candidate)

    return feasible


def select_initial_leader(
    candidates: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Select the preliminary leader using immediate/local criteria.

    This is deliberately NOT the final AERIS decision.

    The final recommendation is allowed to change after:
    - network simulation;
    - stress testing;
    - critic challenge;
    - resilience-aware scoring.

    The preliminary leader is simply the strongest feasible
    candidate on local/immediate score.
    """
    feasible = feasible_candidates(candidates)

    if not feasible:
        raise NoFeasibleCandidateError(
            "No safe candidate satisfies current hard constraints."
        )

    def sort_key(candidate: Dict[str, Any]) -> tuple:
        raw_score = candidate.get(
            "local_score",
            candidate.get("immediate_score", 0.0),
        )

        try:
            local_score = float(raw_score)
        except (TypeError, ValueError):
            local_score = 0.0

        candidate_id = str(
            candidate.get(
                "candidate_id",
                "",
            )
        )

        return (
            -local_score,
            candidate_id,
        )

    return sorted(
        feasible,
        key=sort_key,
    )[0]


class InterventionPlanner:
    """
    Deterministic intervention-selection policy.

    The planner decides which intervention families deserve evaluation.
    It does not perform aviation calculations and does not declare a route
    operationally feasible. Deterministic tools remain authoritative for
    those decisions.
    """

    CANDIDATE_TOOLS: Sequence[str] = (
        "generate_alternatives",
        "validate_candidate",
        "simulate_network_impact",
        "stress_test_candidate",
    )

    def plan(
        self,
        world_state: Any,
        diagnosis: Optional[Any] = None,
    ) -> InterventionPlan:
        state = self._as_dict(world_state)

        scenario_id = str(
            state.get(
                "scenario_id",
                "unknown_scenario",
            )
        )

        target_flight = self._as_dict(
            state.get(
                "target_flight",
                {},
            )
        )

        target_flight_id = str(
            target_flight.get(
                "id",
                state.get(
                    "target_flight_id",
                    "unknown_flight",
                ),
            )
        )

        signals = self._extract_signals(
            state,
            diagnosis,
        )

        priorities = self._build_priorities(
            signals
        )

        ranked = sorted(
            priorities.items(),
            key=lambda item: (
                -item[1],
                item[0].value,
            ),
        )

        actionable = [
            intervention_type
            for intervention_type, priority in ranked
            if (
                intervention_type
                != InterventionType.MONITOR
                and priority > 0
            )
        ]

        if not actionable:
            primary = InterventionType.MONITOR
            generate_candidates = False
        else:
            primary = actionable[0]
            generate_candidates = True

        intents = self._build_intents(
            ranked=ranked,
            signals=signals,
            generate_candidates=generate_candidates,
        )

        rationale = self._build_rationale(
            primary=primary,
            signals=signals,
            intents=intents,
        )

        evidence_signals = (
            self._build_evidence_signals(
                signals
            )
        )

        return InterventionPlan(
            scenario_id=scenario_id,
            target_flight_id=target_flight_id,
            primary_intervention=primary,
            intervention_intents=intents,
            candidate_budget=min(
                5,
                max(
                    1,
                    len(actionable),
                ),
            ),
            generate_candidates=generate_candidates,
            rationale=rationale,
            evidence_signals=evidence_signals,
            fallback_intervention=(
                InterventionType.MONITOR
            ),
        )

    def _extract_signals(
        self,
        world_state: Dict[str, Any],
        diagnosis: Optional[Any],
    ) -> PlannerSignals:
        target_flight = self._as_dict(
            world_state.get(
                "target_flight",
                {},
            )
        )

        airports = self._as_list(
            world_state.get(
                "airports",
                [],
            )
        )

        sectors = self._as_list(
            world_state.get(
                "sectors",
                [],
            )
        )

        weather_cells = self._as_list(
            world_state.get(
                "weather_cells",
                [],
            )
        )

        alerts = self._as_list(
            world_state.get(
                "alerts",
                [],
            )
        )

        network_summary = self._as_dict(
            world_state.get(
                "network_summary",
                {},
            )
        )

        weather_severities = {
            str(
                self._as_dict(cell).get(
                    "severity",
                    "",
                )
            ).upper()
            for cell in weather_cells
        }

        severe_weather = (
            "SEVERE"
            in weather_severities
        )

        significant_weather = (
            severe_weather
            or "HIGH" in weather_severities
        )

        degraded_airport = any(
            str(
                self._as_dict(airport).get(
                    "operational_status",
                    "",
                )
            ).upper()
            not in {
                "",
                "NORMAL",
                "OPERATIONAL",
            }
            for airport in airports
        )

        stressed_sector = any(
            self._sector_is_stressed(
                self._as_dict(sector)
            )
            for sector in sectors
        )

        fuel_remaining = self._safe_float(
            target_flight.get(
                "fuel_remaining_min"
            )
        )

        reserve_required = self._safe_float(
            target_flight.get(
                "reserve_required_min"
            )
        )

        fuel_margin: Optional[float] = None

        if (
            fuel_remaining is not None
            and reserve_required is not None
        ):
            fuel_margin = (
                fuel_remaining
                - reserve_required
            )

        low_fuel_margin = (
            fuel_margin is not None
            and fuel_margin < 75
        )

        critical_fuel_margin = (
            fuel_margin is not None
            and fuel_margin < 60
        )

        target_status = str(
            target_flight.get(
                "status",
                "",
            )
        ).upper()

        urgency = str(
            world_state.get(
                "urgency",
                target_flight.get(
                    "urgency",
                    "",
                ),
            )
        ).upper()

        active_holding = (
            (
                self._safe_int(
                    network_summary.get(
                        "aircraft_in_holding"
                    )
                )
                or 0
            )
            > 0
        )

        disruption_present = (
            any(alerts)
            or any(
                str(
                    self._as_dict(cell).get(
                        "severity",
                        "",
                    )
                ).upper()
                not in {
                    "",
                    "NORMAL",
                    "LOW",
                }
                for cell in weather_cells
            )
            or degraded_airport
            or stressed_sector
        )

        if diagnosis is not None:
            diagnosis_dict = self._as_dict(
                diagnosis
            )

            diagnosis_text = str(
                diagnosis_dict.get(
                    "summary",
                    "",
                )
            ).lower()

            if any(
                token in diagnosis_text
                for token in (
                    "weather",
                    "convective",
                    "storm",
                )
            ):
                significant_weather = True

            if any(
                token in diagnosis_text
                for token in (
                    "airport",
                    "capacity",
                )
            ):
                degraded_airport = True

            if any(
                token in diagnosis_text
                for token in (
                    "sector",
                    "congestion",
                    "overload",
                )
            ):
                stressed_sector = True

        return PlannerSignals(
            severe_weather=severe_weather,
            significant_weather=significant_weather,
            degraded_airport=degraded_airport,
            stressed_sector=stressed_sector,
            target_degraded=target_status
            in {
                "DEGRADED",
                "AT_RISK",
                "CRITICAL",
            },
            active_holding=active_holding,
            high_urgency=urgency
            in {
                "HIGH",
                "CRITICAL",
            },
            low_fuel_margin=low_fuel_margin,
            critical_fuel_margin=critical_fuel_margin,
            disruption_present=(
                disruption_present
            ),
        )

    def _build_priorities(
        self,
        signals: PlannerSignals,
    ) -> Dict[InterventionType, int]:
        priorities: Dict[
            InterventionType,
            int,
        ] = {
            InterventionType.REROUTE: 0,
            InterventionType.ALTITUDE_SPEED: 0,
            InterventionType.TIMING_HOLD: 0,
            InterventionType.ALTERNATE_DIVERSION: 0,
            InterventionType.MONITOR: 25,
        }

        if signals.significant_weather:
            priorities[
                InterventionType.REROUTE
            ] += 55

            priorities[
                InterventionType.ALTITUDE_SPEED
            ] += 35

        if signals.severe_weather:
            priorities[
                InterventionType.REROUTE
            ] += 15

            priorities[
                InterventionType.ALTITUDE_SPEED
            ] += 15

            priorities[
                InterventionType.ALTERNATE_DIVERSION
            ] += 10

        if signals.stressed_sector:
            priorities[
                InterventionType.REROUTE
            ] += 25

            priorities[
                InterventionType.ALTITUDE_SPEED
            ] += 20

        if signals.degraded_airport:
            priorities[
                InterventionType.TIMING_HOLD
            ] += 35

            priorities[
                InterventionType.ALTERNATE_DIVERSION
            ] += 40

        if signals.active_holding:
            priorities[
                InterventionType.TIMING_HOLD
            ] += 30

        if signals.low_fuel_margin:
            priorities[
                InterventionType.ALTERNATE_DIVERSION
            ] += 30

            priorities[
                InterventionType.TIMING_HOLD
            ] += 10

        if signals.critical_fuel_margin:
            priorities[
                InterventionType.ALTERNATE_DIVERSION
            ] += 25

            priorities[
                InterventionType.REROUTE
            ] -= 10

        if signals.target_degraded:
            priorities[
                InterventionType.REROUTE
            ] += 15

            priorities[
                InterventionType.ALTITUDE_SPEED
            ] += 10

            priorities[
                InterventionType.TIMING_HOLD
            ] += 10

        if signals.high_urgency:
            priorities[
                InterventionType.MONITOR
            ] = 5

        if not signals.disruption_present:
            priorities[
                InterventionType.MONITOR
            ] = 100

        for intervention_type in (
            InterventionType.REROUTE,
            InterventionType.ALTITUDE_SPEED,
            InterventionType.TIMING_HOLD,
            InterventionType.ALTERNATE_DIVERSION,
        ):
            priorities[intervention_type] = max(
                0,
                min(
                    100,
                    priorities[
                        intervention_type
                    ],
                ),
            )

        return priorities

    def _build_intents(
        self,
        ranked: Iterable[Any],
        signals: PlannerSignals,
        generate_candidates: bool,
    ) -> List[InterventionIntent]:
        intents: List[
            InterventionIntent
        ] = []

        rationale_by_type = {
            InterventionType.REROUTE:
                (
                    "Evaluate spatially separated "
                    "alternatives that redistribute "
                    "demand away from the disrupted corridor."
                ),
            InterventionType.ALTITUDE_SPEED:
                (
                    "Evaluate vertical or speed-management "
                    "options that can reduce sector loading "
                    "without requiring the same lateral bypass."
                ),
            InterventionType.TIMING_HOLD:
                (
                    "Evaluate controlled timing changes when "
                    "arrival capacity or downstream congestion "
                    "makes immediate routing insufficient."
                ),
            InterventionType.ALTERNATE_DIVERSION:
                (
                    "Evaluate alternate-airport or diversion-"
                    "oriented options when destination degradation "
                    "or fuel uncertainty increases downstream risk."
                ),
            InterventionType.MONITOR:
                (
                    "Continue observation without generating "
                    "a consequential intervention."
                ),
        }

        for intervention_type, priority in list(
            ranked
        ):
            if priority <= 0:
                continue

            if (
                intervention_type
                == InterventionType.MONITOR
            ):
                intents.append(
                    InterventionIntent(
                        intervention_type=(
                            intervention_type
                        ),
                        priority=priority,
                        rationale=(
                            rationale_by_type[
                                intervention_type
                            ]
                        ),
                        required_tools=[
                            "get_network_metrics"
                        ],
                        candidate_generation=False,
                    )
                )
                continue

            intents.append(
                InterventionIntent(
                    intervention_type=(
                        intervention_type
                    ),
                    priority=priority,
                    rationale=(
                        rationale_by_type[
                            intervention_type
                        ]
                    ),
                    required_tools=list(
                        self.CANDIDATE_TOOLS
                    ),
                    candidate_generation=(
                        generate_candidates
                    ),
                )
            )

        return intents

    def _build_rationale(
        self,
        primary: InterventionType,
        signals: PlannerSignals,
        intents: List[InterventionIntent],
    ) -> str:
        active_factors: List[str] = []

        if signals.significant_weather:
            active_factors.append(
                "weather pressure"
            )

        if signals.degraded_airport:
            active_factors.append(
                "airport capacity degradation"
            )

        if signals.stressed_sector:
            active_factors.append(
                "stressed sector capacity"
            )

        if signals.active_holding:
            active_factors.append(
                "holding demand"
            )

        if signals.low_fuel_margin:
            active_factors.append(
                "reduced fuel buffer"
            )

        if signals.target_degraded:
            active_factors.append(
                "target-flight degradation"
            )

        if not active_factors:
            return (
                "No material intervention trigger is active. "
                "AERIS should continue monitoring rather than "
                "generate a consequential candidate."
            )

        secondary = [
            intent.intervention_type.value
            for intent in intents
            if (
                intent.intervention_type
                != primary
                and intent.intervention_type
                != InterventionType.MONITOR
            )
        ]

        if secondary:
            return (
                f"Primary intervention: {primary.value}. "
                f"Observed drivers: {', '.join(active_factors)}. "
                f"Also evaluate: {', '.join(secondary)}. "
                "Candidate generation remains subordinate to "
                "deterministic validation, network simulation, "
                "and future stress testing."
            )

        return (
            f"Primary intervention: {primary.value}. "
            f"Observed drivers: {', '.join(active_factors)}. "
            "Candidate generation remains subordinate to "
            "deterministic validation, network simulation, "
            "and future stress testing."
        )

    def _build_evidence_signals(
        self,
        signals: PlannerSignals,
    ) -> List[str]:
        evidence: List[str] = []

        if signals.significant_weather:
            evidence.append(
                "WEATHER_PRESSURE"
            )

        if signals.degraded_airport:
            evidence.append(
                "AIRPORT_CAPACITY_DEGRADATION"
            )

        if signals.stressed_sector:
            evidence.append(
                "SECTOR_CONGESTION"
            )

        if signals.active_holding:
            evidence.append(
                "HOLDING_DEMAND"
            )

        if signals.low_fuel_margin:
            evidence.append(
                "LOW_FUEL_BUFFER"
            )

        if signals.target_degraded:
            evidence.append(
                "TARGET_FLIGHT_DEGRADED"
            )

        if signals.high_urgency:
            evidence.append(
                "HIGH_URGENCY"
            )

        return evidence

    @staticmethod
    def _sector_is_stressed(
        sector: Dict[str, Any],
    ) -> bool:
        status = str(
            sector.get(
                "status",
                "",
            )
        ).upper()

        if status in {
            "STRESSED",
            "CONGESTED",
            "OVERLOADED",
            "CRITICAL",
        }:
            return True

        utilization = (
            InterventionPlanner._safe_float(
                sector.get(
                    "projected_utilization"
                )
            )
        )

        return (
            utilization is not None
            and utilization >= 0.85
        )

    @staticmethod
    def _safe_float(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        try:
            return float(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _safe_int(
        value: Any,
    ) -> Optional[int]:
        if value is None:
            return None

        try:
            return int(value)
        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _as_dict(
        value: Any,
    ) -> Dict[str, Any]:
        if isinstance(
            value,
            BaseModel,
        ):
            return value.model_dump()

        if isinstance(
            value,
            dict,
        ):
            return value

        if hasattr(
            value,
            "dict",
        ):
            try:
                return value.dict()
            except TypeError:
                pass

        return {}

    @staticmethod
    def _as_list(
        value: Any,
    ) -> List[Any]:
        if isinstance(
            value,
            list,
        ):
            return value

        if isinstance(
            value,
            tuple,
        ):
            return list(value)

        return []