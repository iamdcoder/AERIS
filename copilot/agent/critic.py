from typing import Any, Mapping

from .state import CriticResult


def criticise_candidate(
    candidate: Mapping[str, Any],
    stress_result: Mapping[str, Any] | None,
) -> CriticResult:
    candidate_id = str(
        candidate.get("candidate_id")
    )

    if not stress_result:
        return CriticResult(
            candidate_id=candidate_id,
            challenged=False,
            finding=(
                "No stress-test evidence is available yet; "
                "recommendation should remain provisional."
            ),
            trigger_conditions=[
                "missing_stress_test_evidence"
            ],
        )

    passed = int(
        stress_result.get("passed", 0)
    )

    total = int(
        stress_result.get("total", 0)
    )

    if stress_result.get("survival_pct") is not None:
        survival = float(stress_result["survival_pct"]) / 100.0
    else:
        # Legacy mock fixtures expose only passed/total.
        survival = passed / total if total else 0.0

    critical_failure = stress_result.get(
        "critical_failure"
    )

    challenged = (
        bool(critical_failure)
        or survival < 0.80
    )

    if challenged:
        finding = (
            f"{candidate_id} is vulnerable under future "
            f"conditions: survives {passed}/{total} scenarios."
        )

        if critical_failure:
            finding += (
                f" Critical failure: {critical_failure}."
            )

        severity = (
            "HIGH"
            if survival < 0.60
            else "MEDIUM"
        )
    else:
        finding = (
            f"{candidate_id} survives {passed}/{total} "
            f"tested scenarios without a critical failure."
        )

        severity = "LOW"

    return CriticResult(
        candidate_id=candidate_id,
        challenged=challenged,
        severity=severity,
        finding=finding,
        trigger_conditions=(
            [critical_failure]
            if critical_failure
            else []
        ),
    )
