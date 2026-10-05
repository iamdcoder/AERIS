from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from pydantic import BaseModel, Field


class DecisionWeights(BaseModel):
    target_flight_benefit: float = 0.25
    network_resilience: float = 0.25
    network_impact_score: float = 0.20
    fuel_safety_margin: float = 0.15
    future_robustness: float = 0.15

    def validate_total(self) -> None:
        total = sum(
            (
                self.target_flight_benefit,
                self.network_resilience,
                self.network_impact_score,
                self.fuel_safety_margin,
                self.future_robustness,
            )
        )

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Decision weights must sum to 1.0, got {total:.6f}"
            )


class ScoreNormalizationConfig(BaseModel):
    target_delay_ceiling_min: float = 15.0
    network_delay_sensitivity_min: float = 20.0
    fuel_margin_floor_kg: float = 0.0
    fuel_margin_target_kg: float = 600.0
    safe_sector_utilization: float = 0.80


class CandidateMetrics(BaseModel):
    candidate_id: str

    feasible: bool

    target_delay_min: Optional[float] = None
    added_distance_km: Optional[float] = None
    fuel_margin_kg: Optional[float] = None
    affected_flights: Optional[int] = None
    network_delay_delta_min: Optional[float] = None
    peak_sector_utilization: Optional[float] = None

    network_resilience: Optional[float] = None

    stress_passed: Optional[int] = None
    stress_total: Optional[int] = None

    second_intervention_probability: Optional[float] = None

    local_score: Optional[float] = None

    rejection_reasons: List[str] = Field(default_factory=list)


class ScoreComponents(BaseModel):
    target_flight_benefit: float
    network_resilience: float
    network_impact_score: float
    fuel_safety_margin: float
    future_robustness: float


class CandidateDecisionScore(BaseModel):
    candidate_id: str
    feasible: bool
    recommendable: bool = True
    recommendation_blockers: List[str] = Field(default_factory=list)

    score: float

    components: ScoreComponents
    raw_metrics: CandidateMetrics

    second_intervention_probability: float
    decision_regret: float = 0.0
    local_regret: float = 0.0

    explanation: str


class DecisionScoreResult(BaseModel):
    weights: DecisionWeights
    normalization: ScoreNormalizationConfig
    scores: List[CandidateDecisionScore]

    ranked_candidate_ids: List[str] = Field(default_factory=list)
    recommended_candidate_id: Optional[str] = None


class DecisionScorer:
    """
    Deterministic, explainable multi-objective scorer.

    The scorer does not determine operational feasibility.
    That comes from the deterministic constraint engine.

    It only evaluates already-returned candidate evidence.
    """

    def __init__(
        self,
        weights: Optional[DecisionWeights] = None,
        normalization: Optional[ScoreNormalizationConfig] = None,
    ) -> None:
        self.weights = weights or DecisionWeights()
        self.weights.validate_total()

        self.normalization = (
            normalization
            or ScoreNormalizationConfig()
        )

    def score_candidate(
        self,
        candidate: Mapping[str, Any],
        simulation: Optional[Mapping[str, Any]] = None,
        stress_test: Optional[Mapping[str, Any]] = None,
    ) -> CandidateDecisionScore:
        metrics = self._build_metrics(
            candidate=candidate,
            simulation=simulation,
            stress_test=stress_test,
        )

        components = self._build_components(metrics)

        score = self._weighted_score(components)

        second_intervention_probability = (
            self._second_intervention_probability(
                metrics=metrics,
                future_robustness=components.future_robustness,
            )
        )

        explanation = self._build_explanation(
            metrics=metrics,
            components=components,
            score=score,
            second_intervention_probability=second_intervention_probability,
        )

        return CandidateDecisionScore(
            candidate_id=metrics.candidate_id,
            feasible=metrics.feasible,
            score=score,
            components=components,
            raw_metrics=metrics,
            second_intervention_probability=second_intervention_probability,
            explanation=explanation,
        )

    def score_candidates(
        self,
        candidates: Iterable[Mapping[str, Any]],
        simulations: Optional[Any] = None,
        stress_tests: Optional[Any] = None,
    ) -> DecisionScoreResult:
        simulation_map = self._index_results(simulations)
        stress_map = self._index_results(stress_tests)

        scores: List[CandidateDecisionScore] = []

        for candidate in candidates:
            candidate_id = self._candidate_id(candidate)

            score = self.score_candidate(
                candidate=candidate,
                simulation=simulation_map.get(candidate_id),
                stress_test=stress_map.get(candidate_id),
            )

            scores.append(score)

        ranked = sorted(
            scores,
            key=lambda item: (
                not item.feasible,
                -item.score if item.feasible else 0.0,
                item.candidate_id,
            ),
        )

        feasible_scores = [
            item
            for item in ranked
            if item.feasible
        ]

        best_score = (
            feasible_scores[0].score
            if feasible_scores
            else 0.0
        )

        best_local_score = self._best_local_score(
            feasible_scores
        )

        for item in scores:
            item.decision_regret = round(
                max(
                    0.0,
                    best_score - item.score,
                ),
                4,
            )

            if item.raw_metrics.local_score is not None:
                item.local_regret = round(
                    max(
                        0.0,
                        best_local_score
                        - item.raw_metrics.local_score,
                    ),
                    4,
                )

        return DecisionScoreResult(
            weights=self.weights,
            normalization=self.normalization,
            scores=scores,
            ranked_candidate_ids=[
                item.candidate_id
                for item in ranked
            ],
            recommended_candidate_id=(
                feasible_scores[0].candidate_id
                if feasible_scores
                else None
            ),
        )

    def _build_metrics(
        self,
        candidate: Mapping[str, Any],
        simulation: Optional[Mapping[str, Any]],
        stress_test: Optional[Mapping[str, Any]],
    ) -> CandidateMetrics:
        candidate_id = self._candidate_id(candidate)

        feasible = self._extract_bool(
            candidate,
            keys=(
                "feasible",
                "valid",
                "is_feasible",
            ),
            default=True,
        )

        rejection_reasons = self._extract_string_list(
            candidate,
            keys=(
                "rejection_reasons",
                "reasons",
                "constraint_failures",
                "blockers",
            ),
        )

        target_delay = self._first_number(
            candidate,
            (
                "target_delay_min",
                "target_delay",
                "delay_min",
            ),
        )

        added_distance = self._first_number(
            candidate,
            (
                "added_distance_km",
                "added_distance",
                "distance_delta_km",
            ),
        )

        fuel_margin = self._first_number(
            candidate,
            (
                "fuel_margin_kg",
                "fuel_margin",
                "reserve_margin_kg",
            ),
        )

        affected_flights = self._first_int(
            candidate,
            (
                "affected_flights",
                "affected_aircraft",
                "network_affected_flights",
            ),
        )

        network_delay = self._first_number(
            simulation,
            (
                "network_delay_delta_min",
                "network_delay_change_min",
                "network_delay",
                "total_network_delay_change",
            ),
        )

        if network_delay is None:
            network_delay = self._first_number(
                candidate,
                (
                    "network_delay_delta_min",
                    "network_delay_change_min",
                    "network_delay",
                ),
            )

        peak_utilization = self._first_number(
            simulation,
            (
                "peak_sector_utilization",
                "max_sector_utilization",
                "sector_peak_utilization",
            ),
        )

        if peak_utilization is None:
            peak_utilization = self._first_number(
                candidate,
                (
                    "peak_sector_utilization",
                    "max_sector_utilization",
                    "sector_peak_utilization",
                ),
            )

        network_resilience = self._first_number(
            candidate,
            (
                "network_resilience",
                "resilience",
                "resilience_score",
            ),
        )

        stress_passed, stress_total = self._stress_counts(
            candidate=candidate,
            stress_test=stress_test,
        )

        second_intervention_probability = self._first_number(
            stress_test,
            (
                "second_intervention_probability",
                "reintervention_probability",
                "re_intervention_probability",
            ),
        )

        if second_intervention_probability is None:
            second_intervention_probability = self._first_number(
                candidate,
                (
                    "second_intervention_probability",
                    "reintervention_probability",
                    "re_intervention_probability",
                ),
            )

        local_score = self._first_number(
            candidate,
            (
                "local_score",
                "immediate_score",
            ),
        )

        return CandidateMetrics(
            candidate_id=candidate_id,
            feasible=feasible,
            target_delay_min=target_delay,
            added_distance_km=added_distance,
            fuel_margin_kg=fuel_margin,
            affected_flights=affected_flights,
            network_delay_delta_min=network_delay,
            peak_sector_utilization=peak_utilization,
            network_resilience=network_resilience,
            stress_passed=stress_passed,
            stress_total=stress_total,
            second_intervention_probability=(
                second_intervention_probability
            ),
            local_score=local_score,
            rejection_reasons=rejection_reasons,
        )

    def _build_components(
        self,
        metrics: CandidateMetrics,
    ) -> ScoreComponents:
        target_benefit = self._target_flight_benefit(
            metrics.target_delay_min
        )

        network_resilience = self._network_resilience(
            resilience=metrics.network_resilience,
            peak_sector_utilization=metrics.peak_sector_utilization,
        )

        network_impact = self._network_impact_score(
            metrics.network_delay_delta_min
        )

        fuel_safety = self._fuel_safety_margin(
            metrics.fuel_margin_kg
        )

        future_robustness = self._future_robustness(
            stress_passed=metrics.stress_passed,
            stress_total=metrics.stress_total,
        )

        return ScoreComponents(
            target_flight_benefit=target_benefit,
            network_resilience=network_resilience,
            network_impact_score=network_impact,
            fuel_safety_margin=fuel_safety,
            future_robustness=future_robustness,
        )

    def _weighted_score(
        self,
        components: ScoreComponents,
    ) -> float:
        score = (
            self.weights.target_flight_benefit
            * components.target_flight_benefit
            + self.weights.network_resilience
            * components.network_resilience
            + self.weights.network_impact_score
            * components.network_impact_score
            + self.weights.fuel_safety_margin
            * components.fuel_safety_margin
            + self.weights.future_robustness
            * components.future_robustness
        )

        return round(
            self._clamp(score),
            4,
        )

    def _target_flight_benefit(
        self,
        target_delay_min: Optional[float],
    ) -> float:
        if target_delay_min is None:
            return 0.5

        if target_delay_min <= 0:
            return 1.0

        ceiling = self.normalization.target_delay_ceiling_min

        if ceiling <= 0:
            return 0.0

        return round(
            self._clamp(
                1.0 - target_delay_min / ceiling
            ),
            4,
        )

    def _network_resilience(
        self,
        resilience: Optional[float],
        peak_sector_utilization: Optional[float],
    ) -> float:
        resilience_component = (
            self._clamp(resilience)
            if resilience is not None
            else 0.5
        )

        if peak_sector_utilization is None:
            return round(
                resilience_component,
                4,
            )

        utilization_component = self._clamp(
            1.0 - peak_sector_utilization
        )

        if resilience is None:
            return round(
                utilization_component,
                4,
            )

        combined = (
            0.70 * resilience_component
            + 0.30 * utilization_component
        )

        return round(
            self._clamp(combined),
            4,
        )

    def _network_impact_score(
        self,
        network_delay_delta_min: Optional[float],
    ) -> float:
        if network_delay_delta_min is None:
            return 0.5

        sensitivity = (
            self.normalization.network_delay_sensitivity_min
        )

        if sensitivity <= 0:
            return 0.5

        # Negative network delay = improvement = higher score.
        score = 0.5 - (
            network_delay_delta_min / sensitivity
        )

        return round(
            self._clamp(score),
            4,
        )

    def _fuel_safety_margin(
        self,
        fuel_margin_kg: Optional[float],
    ) -> float:
        if fuel_margin_kg is None:
            return 0.5

        floor = self.normalization.fuel_margin_floor_kg
        target = self.normalization.fuel_margin_target_kg

        if target <= floor:
            return 0.0

        score = (
            fuel_margin_kg - floor
        ) / (
            target - floor
        )

        return round(
            self._clamp(score),
            4,
        )

    def _future_robustness(
        self,
        stress_passed: Optional[int],
        stress_total: Optional[int],
    ) -> float:
        if stress_passed is None or stress_total is None:
            return 0.5

        if stress_total <= 0:
            return 0.0

        return round(
            self._clamp(
                stress_passed / stress_total
            ),
            4,
        )

    def _second_intervention_probability(
        self,
        metrics: CandidateMetrics,
        future_robustness: float,
    ) -> float:
        if metrics.second_intervention_probability is not None:
            return round(
                self._clamp(
                    metrics.second_intervention_probability
                ),
                4,
            )

        # Deterministic proxy when the stress-test output does not
        # explicitly provide a re-intervention probability.
        return round(
            self._clamp(
                1.0 - future_robustness
            ),
            4,
        )

    def _build_explanation(
        self,
        metrics: CandidateMetrics,
        components: ScoreComponents,
        score: float,
        second_intervention_probability: float,
    ) -> str:
        network_effect = (
            "improves the network"
            if (
                metrics.network_delay_delta_min is not None
                and metrics.network_delay_delta_min < 0
            )
            else "adds network delay"
            if (
                metrics.network_delay_delta_min is not None
                and metrics.network_delay_delta_min > 0
            )
            else "has neutral network-delay impact"
        )

        robustness = (
            f"{metrics.stress_passed}/{metrics.stress_total}"
            if (
                metrics.stress_passed is not None
                and metrics.stress_total is not None
            )
            else "unknown"
        )

        return (
            f"{metrics.candidate_id}: AERIS score {score:.2f}. "
            f"Target-benefit component {components.target_flight_benefit:.2f}; "
            f"network-resilience component {components.network_resilience:.2f}; "
            f"network-impact component {components.network_impact_score:.2f}; "
            f"fuel-safety component {components.fuel_safety_margin:.2f}; "
            f"future-robustness component {components.future_robustness:.2f}. "
            f"The candidate {network_effect}. "
            f"Stress survival: {robustness}. "
            f"Estimated second-intervention probability: "
            f"{second_intervention_probability:.0%}."
        )

    @staticmethod
    def _best_local_score(
        feasible_scores: List[CandidateDecisionScore],
    ) -> float:
        values = [
            item.raw_metrics.local_score
            for item in feasible_scores
            if item.raw_metrics.local_score is not None
        ]

        return max(values) if values else 0.0

    @classmethod
    def _stress_counts(
        cls,
        candidate: Mapping[str, Any],
        stress_test: Optional[Mapping[str, Any]],
    ) -> tuple[Optional[int], Optional[int]]:
        passed = cls._first_int(
            stress_test,
            (
                "scenarios_passed",
                "passed",
                "pass_count",
                "survived_scenarios",
            ),
        )

        total = cls._first_int(
            stress_test,
            (
                "scenarios_total",
                "total",
                "scenario_count",
                "total_scenarios",
            ),
        )

        if passed is None:
            passed = cls._first_int(
                candidate,
                (
                    "scenarios_passed",
                    "survival_passed",
                    "stress_passed",
                ),
            )

        if total is None:
            total = cls._first_int(
                candidate,
                (
                    "scenarios_total",
                    "survival_total",
                    "stress_total",
                ),
            )

        survival = cls._first_string(
            candidate,
            (
                "scenario_survival",
                "stress_test_survival",
                "survival",
            ),
        )

        if survival and (passed is None or total is None):
            parsed_passed, parsed_total = cls._parse_fraction(
                survival
            )

            if passed is None:
                passed = parsed_passed

            if total is None:
                total = parsed_total

        survival = cls._first_string(
            stress_test,
            (
                "scenario_survival",
                "stress_test_survival",
                "survival",
            ),
        )

        if survival and (passed is None or total is None):
            parsed_passed, parsed_total = cls._parse_fraction(
                survival
            )

            if passed is None:
                passed = parsed_passed

            if total is None:
                total = parsed_total

        return passed, total

    @staticmethod
    def _index_results(
        results: Optional[Any],
    ) -> Dict[str, Dict[str, Any]]:
        if results is None:
            return {}

        if isinstance(results, Mapping):
            if "candidates" in results:
                results = results["candidates"]

            elif "alternatives" in results:
                results = results["alternatives"]

            elif "results" in results:
                results = results["results"]

            else:
                maybe_single = DecisionScorer._candidate_id(
                    results
                )

                if maybe_single != "UNKNOWN":
                    return {
                        maybe_single: dict(results)
                    }

        if not isinstance(results, Iterable):
            return {}

        indexed: Dict[str, Dict[str, Any]] = {}

        for item in results:
            if not isinstance(item, Mapping):
                continue

            candidate_id = DecisionScorer._candidate_id(item)

            indexed[candidate_id] = dict(item)

        return indexed

    @staticmethod
    def _candidate_id(
        candidate: Optional[Mapping[str, Any]],
    ) -> str:
        if candidate is None:
            return "UNKNOWN"

        for key in (
            "candidate_id",
            "id",
            "route_id",
            "alternative_id",
        ):
            value = candidate.get(key)

            if value is not None:
                return str(value)

        return "UNKNOWN"

    @staticmethod
    def _first_number(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[float]:
        if source is None:
            return None

        for key in keys:
            value = source.get(key)

            if value is None:
                continue

            try:
                return float(value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _first_int(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[int]:
        if source is None:
            return None

        for key in keys:
            value = source.get(key)

            if value is None:
                continue

            try:
                return int(value)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _first_string(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[str]:
        if source is None:
            return None

        for key in keys:
            value = source.get(key)

            if value is None:
                continue

            return str(value)

        return None

    @staticmethod
    def _extract_bool(
        source: Mapping[str, Any],
        keys: tuple[str, ...],
        default: bool,
    ) -> bool:
        for key in keys:
            if key not in source:
                continue

            value = source[key]

            if isinstance(value, bool):
                return value

            if isinstance(value, str):
                normalized = value.strip().lower()

                if normalized in {
                    "true",
                    "yes",
                    "1",
                    "feasible",
                    "valid",
                }:
                    return True

                if normalized in {
                    "false",
                    "no",
                    "0",
                    "infeasible",
                    "invalid",
                }:
                    return False

        return default

    @staticmethod
    def _extract_string_list(
        source: Mapping[str, Any],
        keys: tuple[str, ...],
    ) -> List[str]:
        for key in keys:
            value = source.get(key)

            if isinstance(value, list):
                return [
                    str(item)
                    for item in value
                    if item is not None
                ]

            if isinstance(value, str) and value.strip():
                return [value.strip()]

        return []

    @staticmethod
    def _parse_fraction(
        value: str,
    ) -> tuple[Optional[int], Optional[int]]:
        cleaned = value.strip()

        if "/" not in cleaned:
            return None, None

        left, right = cleaned.split(
            "/",
            maxsplit=1,
        )

        try:
            return int(left.strip()), int(right.strip())
        except ValueError:
            return None, None

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                value,
            ),
        )