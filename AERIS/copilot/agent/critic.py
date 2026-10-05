from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field

from copilot.agent.ranker import RankingSummary
from copilot.agent.scoring import CandidateDecisionScore


class CriticFinding(BaseModel):
    category: str
    severity: str
    condition: str
    evidence: str
    mitigation: Optional[str] = None


class CriticResult(BaseModel):
    candidate_id: str
    challenged: bool
    challenge_severity: str

    findings: List[CriticFinding] = Field(
        default_factory=list
    )

    failure_modes_checked: List[str] = Field(
        default_factory=list
    )

    surviving_checks: List[str] = Field(
        default_factory=list
    )

    should_reconsider: bool = False
    replacement_candidate_id: Optional[str] = None

    summary: str


class DecisionCritic:
    """
    Deterministic adversarial critic.

    The critic does not invent aviation events and does not calculate
    operational feasibility. It inspects evidence already produced by
    deterministic tools and stress tests.

    The core question is:

        "What plausible condition would make this decision fail?"
    """

    FAILURE_MODES = (
        "WORSENING_WEATHER",
        "REDUCED_SECTOR_CAPACITY",
        "INCREASED_TRAFFIC",
        "NEW_RESTRICTION",
        "DOWNSTREAM_AIRPORT_DEGRADATION",
    )

    def review(
        self,
        leader: CandidateDecisionScore,
        ranking: RankingSummary,
        stress_test: Optional[Mapping[str, Any]] = None,
        simulation: Optional[Mapping[str, Any]] = None,
    ) -> CriticResult:
        failures_checked = list(self.FAILURE_MODES)

        findings: List[CriticFinding] = []
        surviving_checks: List[str] = []

        stress_test = stress_test or {}
        simulation = simulation or {}

        passed, total = self._stress_counts(
            leader,
            stress_test,
        )

        peak_utilization = self._number(
            simulation,
            (
                "peak_sector_utilization",
                "max_sector_utilization",
                "sector_peak_utilization",
            ),
        )

        conflict_count = self._int(
            simulation,
            (
                "new_conflicts",
                "new_conflict_count",
                "conflict_count",
            ),
        )

        downstream_status = self._text(
            simulation,
            (
                "downstream_risk",
                "downstream_impact",
                "cascade_level",
            ),
        )

        second_intervention_probability = (
            leader.second_intervention_probability
        )

        if (
            passed is not None
            and total is not None
            and total > 0
        ):
            survival_ratio = passed / total

            if survival_ratio < 0.60:
                findings.append(
                    CriticFinding(
                        category="FUTURE_ROBUSTNESS",
                        severity="CRITICAL",
                        condition=(
                            "The candidate fails a majority of "
                            "tested future scenarios."
                        ),
                        evidence=(
                            f"Stress-test survival is "
                            f"{passed}/{total}."
                        ),
                        mitigation=(
                            "Reconsider the candidate and evaluate "
                            "the strongest surviving alternative."
                        ),
                    )
                )

            elif survival_ratio < 0.80:
                findings.append(
                    CriticFinding(
                        category="FUTURE_ROBUSTNESS",
                        severity="HIGH",
                        condition=(
                            "The candidate has material future "
                            "scenario fragility."
                        ),
                        evidence=(
                            f"Stress-test survival is "
                            f"{passed}/{total}."
                        ),
                        mitigation=(
                            "Compare against the strongest "
                            "higher-survival candidate."
                        ),
                    )
                )

            else:
                surviving_checks.append(
                    f"Future stress survival {passed}/{total}"
                )

        if (
            peak_utilization is not None
            and peak_utilization > 1.0
        ):
            findings.append(
                CriticFinding(
                    category="SECTOR_CAPACITY",
                    severity="CRITICAL",
                    condition=(
                        "A sector reaches overload under the "
                        "evaluated outcome."
                    ),
                    evidence=(
                        f"Peak sector utilization is "
                        f"{peak_utilization:.0%}."
                    ),
                    mitigation=(
                        "Reject the overloaded candidate or "
                        "re-evaluate with demand redistributed."
                    ),
                )
            )

        elif (
            peak_utilization is not None
            and peak_utilization >= 0.95
        ):
            findings.append(
                CriticFinding(
                    category="SECTOR_CAPACITY",
                    severity="HIGH",
                    condition=(
                        "A sector remains close to capacity."
                    ),
                    evidence=(
                        f"Peak sector utilization is "
                        f"{peak_utilization:.0%}."
                    ),
                    mitigation=(
                        "Prefer a candidate with greater sector "
                        "headroom when other objectives remain acceptable."
                    ),
                )
            )

        elif peak_utilization is not None:
            surviving_checks.append(
                f"Peak sector utilization {peak_utilization:.0%}"
            )

        if conflict_count is not None:
            if conflict_count > 0:
                findings.append(
                    CriticFinding(
                        category="CONFLICT_RISK",
                        severity="CRITICAL",
                        condition=(
                            "The evaluated intervention introduces "
                            "new conflicts."
                        ),
                        evidence=(
                            f"Simulation reports "
                            f"{conflict_count} new conflict(s)."
                        ),
                        mitigation=(
                            "Do not recommend until the conflict "
                            "condition is eliminated."
                        ),
                    )
                )
            else:
                surviving_checks.append(
                    "No new conflicts reported"
                )

        if downstream_status:
            normalized = downstream_status.strip().lower()

            if normalized in {
                "critical",
                "high",
                "severe",
            }:
                findings.append(
                    CriticFinding(
                        category="DOWNSTREAM_IMPACT",
                        severity="HIGH",
                        condition=(
                            "The candidate creates elevated "
                            "downstream network risk."
                        ),
                        evidence=(
                            f"Simulation downstream status: "
                            f"{downstream_status}."
                        ),
                        mitigation=(
                            "Prefer a candidate with lower "
                            "downstream cascade exposure."
                        ),
                    )
                )
            else:
                surviving_checks.append(
                    f"Downstream impact {downstream_status}"
                )

        if second_intervention_probability >= 0.50:
            findings.append(
                CriticFinding(
                    category="REINTERVENTION",
                    severity="HIGH",
                    condition=(
                        "The candidate has a high estimated "
                        "probability of requiring a second intervention."
                    ),
                    evidence=(
                        "Estimated second-intervention probability "
                        f"is {second_intervention_probability:.0%}."
                    ),
                    mitigation=(
                        "Prefer a more robust candidate if available."
                    ),
                )

            )
        else:
            surviving_checks.append(
                f"Second-intervention probability "
                f"{second_intervention_probability:.0%}"
            )

        should_reconsider = any(
            finding.severity in {
                "CRITICAL",
                "HIGH",
            }
            for finding in findings
        )

        replacement_candidate_id = None

        if should_reconsider:
            replacement_candidate_id = (
                self._best_unaffected_alternative(
                    leader=leader,
                    ranking=ranking,
                    findings=findings,
                )
            )

        challenge_severity = self._challenge_severity(
            findings
        )

        summary = self._build_summary(
            leader=leader,
            findings=findings,
            should_reconsider=should_reconsider,
            replacement_candidate_id=replacement_candidate_id,
        )

        return CriticResult(
            candidate_id=leader.candidate_id,
            challenged=bool(findings),
            challenge_severity=challenge_severity,
            findings=findings,
            failure_modes_checked=failures_checked,
            surviving_checks=surviving_checks,
            should_reconsider=should_reconsider,
            replacement_candidate_id=replacement_candidate_id,
            summary=summary,
        )

    def _best_unaffected_alternative(
        self,
        leader: CandidateDecisionScore,
        ranking: RankingSummary,
        findings: List[CriticFinding],
    ) -> Optional[str]:
        problematic_categories = {
            finding.category
            for finding in findings
        }

        ranked = [
            item
            for item in ranking.ranked_candidates
            if item.feasible
            and item.candidate_id != leader.candidate_id
        ]

        for item in ranked:
            if "CONFLICT_RISK" in problematic_categories:
                # The ranking already removed infeasible candidates.
                # A different feasible option is safer than keeping
                # a leader that created a conflict.
                return item.candidate_id

            if (
                "SECTOR_CAPACITY" in problematic_categories
                and item.resilience >= leader.components.network_resilience
            ):
                return item.candidate_id

            if (
                "FUTURE_ROBUSTNESS" in problematic_categories
                and item.future_robustness
                > leader.components.future_robustness
            ):
                return item.candidate_id

            if (
                "REINTERVENTION" in problematic_categories
                and item.second_intervention_probability
                < leader.second_intervention_probability
            ):
                return item.candidate_id

        return None

    @staticmethod
    def _stress_counts(
        leader: CandidateDecisionScore,
        stress_test: Mapping[str, Any],
    ) -> tuple[Optional[int], Optional[int]]:
        passed = DecisionCritic._int(
            stress_test,
            (
                "scenarios_passed",
                "passed",
                "pass_count",
            ),
        )

        total = DecisionCritic._int(
            stress_test,
            (
                "scenarios_total",
                "total",
                "scenario_count",
            ),
        )

        if passed is None:
            passed = leader.raw_metrics.stress_passed

        if total is None:
            total = leader.raw_metrics.stress_total

        return passed, total

    @staticmethod
    def _challenge_severity(
        findings: List[CriticFinding],
    ) -> str:
        severities = {
            finding.severity
            for finding in findings
        }

        if "CRITICAL" in severities:
            return "CRITICAL"

        if "HIGH" in severities:
            return "HIGH"

        if "MEDIUM" in severities:
            return "MEDIUM"

        return "NONE"

    @staticmethod
    def _build_summary(
        leader: CandidateDecisionScore,
        findings: List[CriticFinding],
        should_reconsider: bool,
        replacement_candidate_id: Optional[str],
    ) -> str:
        if not findings:
            return (
                f"Critic reviewed {leader.candidate_id} against "
                "future robustness, capacity, conflicts, downstream "
                "impact and re-intervention risk. No material "
                "failure condition was found."
            )

        categories = ", ".join(
            finding.category
            for finding in findings
        )

        if should_reconsider:
            if replacement_candidate_id:
                return (
                    f"Critic challenged {leader.candidate_id}. "
                    f"Failure categories: {categories}. "
                    f"A stronger surviving alternative is "
                    f"{replacement_candidate_id}."
                )

            return (
                f"Critic challenged {leader.candidate_id}. "
                f"Failure categories: {categories}. "
                "The leader requires reassessment."
            )

        return (
            f"Critic found limited concerns for "
            f"{leader.candidate_id}: {categories}."
        )

    @staticmethod
    def _number(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[float]:
        if not source:
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
    def _int(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[int]:
        if not source:
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
    def _text(
        source: Optional[Mapping[str, Any]],
        keys: tuple[str, ...],
    ) -> Optional[str]:
        if not source:
            return None

        for key in keys:
            value = source.get(key)

            if value is not None:
                return str(value)

        return None