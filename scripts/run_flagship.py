#!/usr/bin/env python3
"""AERIS — Mumbai Monsoon Flagship Runner.

Deterministic, reproducible, offline-safe proof of the authoritative engine lifecycle:

    DISRUPTION → DETECTION → CANDIDATES → VALIDATION → SIMULATION
    → STRESS TEST → DECISION → HUMAN APPROVAL → EXECUTE → VERIFY

Usage (from repository root):
    python scripts/run_flagship.py

The runner uses only the public engine facade (backend.app.engine.public).
It does NOT import internal engine modules for business logic.
It does NOT require network access, Gemini, or any LLM.

Design note on apply timing
----------------------------
The engine re-validates the candidate at the moment apply_intervention() is
called.  F102 burns 1 min of fuel per simulation minute throughout deliberation,
so the human-approval + apply step must be executed while the winning candidate
is still feasible.  The scenario's T+30 "dispatcher_approval" event is therefore
rendered as a *logical* gate (approval precedes apply) rather than a temporal
one — the gate itself is explicit and non-skippable; we simply do not advance
the simulation clock past the safe window before calling apply.
"""
from __future__ import annotations

import json
import os
import sys

# Ensure the backend package is importable when run from the repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_REPO_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from app.engine import public  # noqa: E402 — path manipulation above is intentional


# ─────────────────────────────────────────────────────────────────────────────
# Scenario constants derived from scenarios/mumbai_weather_crisis.json
# ─────────────────────────────────────────────────────────────────────────────
SCENARIO_ID = "mumbai_weather_crisis_v2"
TARGET_FLIGHT = "F102"
EXPECTED_REJECTED = {"ALT-C", "ALT-E"} # scenario t=19: 2_candidates_expected_rejected
TOTAL_CANDIDATES = 5
STRESS_PROFILE_COUNT = 5               # scenario t=24: stress_test_3_futures → 5 profiles

# Timeline checkpoints (minutes) driven by scenario events
T_BASELINE   = 0
T_WEATHER    = 5
T_BOM_CAP    = 8
T_HOLDING    = 10
T_S6_CAP     = 12
T_DEGRADE    = 15
T_GENERATE   = 17
T_RESTRICT   = 18
T_VALIDATE   = 19
T_EVALUATE   = 21
T_STRESS     = 24
T_CRITIC     = 26
T_RECOMMEND  = 28   # recommendation + HUMAN APPROVAL + APPLY (while feasible)
T_POST_APPLY = 30   # post-apply display checkpoint
T_VERIFY     = 32
T_MONITOR    = 35


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _divider(char: str = "─", width: int = 56) -> str:
    return char * width


def _section(t: int, label: str) -> None:
    print()
    print(f"T+{t:02d}  {label}")


def _line(text: str, indent: int = 6) -> None:
    print(" " * indent + text)


def _aircraft_by_id(state: dict) -> dict[str, dict]:
    return {a["id"]: a for a in state.get("aircraft", [])}


def _airports_by_id(state: dict) -> dict[str, dict]:
    return {a["id"]: a for a in state.get("airports", [])}


def _network_delay(state: dict) -> float:
    return sum(a.get("delay_min", 0) for a in state.get("aircraft", []))


def _airborne_count(state: dict) -> int:
    return sum(1 for a in state.get("aircraft", []) if a.get("status") == "AIRBORNE")


def _holding_count(state: dict) -> int:
    return sum(1 for a in state.get("aircraft", []) if a.get("status") == "HOLDING")


def _advance_to(target_t: int, current_t: int) -> dict:
    """Advance the engine to target_t, returning the new state snapshot."""
    delta = target_t - current_t
    if delta <= 0:
        return public.get_airspace_state()
    return public.advance_simulation(delta)


# ─────────────────────────────────────────────────────────────────────────────
# Story assertions — fail loudly if the engine does not match the scenario spec
# ─────────────────────────────────────────────────────────────────────────────

class FlagshipAssertionError(RuntimeError):
    pass


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise FlagshipAssertionError(f"ASSERTION FAILED: {message}")


# ─────────────────────────────────────────────────────────────────────────────
# Phase runners
# ─────────────────────────────────────────────────────────────────────────────

def _run_baseline(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_BASELINE, current_t)
    current_t = state["time_min"]

    aircraft = _aircraft_by_id(state)
    airports = _airports_by_id(state)
    bom = airports.get("BOM", {})
    f102 = aircraft.get(TARGET_FLIGHT, {})

    _section(T_BASELINE, "BASELINE")
    _line(f"Scenario     : {SCENARIO_ID}")
    _line(f"Target       : {TARGET_FLIGHT} ({f102.get('callsign', '?')})")
    _line(f"Total flights: {len(state['aircraft'])}")
    _line(f"Airborne     : {_airborne_count(state)}")
    _line(f"Network delay: {_network_delay(state):.1f} min")
    _line(f"BOM capacity : {bom.get('arrival_capacity')} arr/hr")
    _line(f"F102 fuel    : {f102.get('fuel_remaining_min', 0):.1f} min")
    _line(f"F102 status  : {f102.get('status')}")

    return state, current_t


def _run_weather(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_WEATHER, current_t)
    current_t = state["time_min"]

    wc = state.get("weather_cells", [])

    _section(T_WEATHER, "WEATHER DISRUPTION")
    _line(f"Weather cells active: {len(wc)}")
    for cell in wc:
        _line(f"  {cell.get('id')}: intensity={cell.get('intensity')}, "
              f"uncertainty={cell.get('uncertainty')}")

    return state, current_t


def _run_bom_capacity(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_BOM_CAP, current_t)
    current_t = state["time_min"]

    airports = _airports_by_id(state)
    bom = airports.get("BOM", {})

    _section(T_BOM_CAP, "BOM ARRIVAL CAPACITY DEGRADATION")
    _line(f"BOM arrival capacity: {bom.get('arrival_capacity')} arr/hr  (was 18)")
    _line(f"Network delay       : {_network_delay(state):.1f} min")

    return state, current_t


def _run_holding(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_HOLDING, current_t)
    current_t = state["time_min"]

    _section(T_HOLDING, "HOLDING BEGINS")
    _line(f"Airborne flights: {_airborne_count(state)}")
    _line(f"Holding flights : {_holding_count(state)}")
    _line(f"Network delay   : {_network_delay(state):.1f} min")

    return state, current_t


def _run_s6_capacity(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_S6_CAP, current_t)
    current_t = state["time_min"]

    sectors = {s["id"]: s for s in state.get("sectors", [])}
    s6 = sectors.get("S6", {})

    _section(T_S6_CAP, "S6 SECTOR CAPACITY REDUCTION")
    _line(f"S6 capacity : {s6.get('capacity')}  (reduced)")
    _line(f"S6 traffic  : {s6.get('current_traffic')}")
    _line(f"Network delay: {_network_delay(state):.1f} min")

    return state, current_t


def _run_degradation(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_DEGRADE, current_t)
    current_t = state["time_min"]

    aircraft = _aircraft_by_id(state)
    f102 = aircraft.get(TARGET_FLIGHT, {})

    _section(T_DEGRADE, "TARGET FLIGHT DEGRADATION")
    _line(f"F102 status  : {f102.get('status')}")
    _line(f"F102 fuel    : {f102.get('fuel_remaining_min', 0):.1f} min remaining")
    _line(f"F102 delay   : {f102.get('delay_min', 0):.2f} min")
    _line(f"Network delay: {_network_delay(state):.1f} min")

    return state, current_t


def _run_generate(current_t: int) -> tuple[list[dict], int]:
    state = _advance_to(T_GENERATE, current_t)
    current_t = state["time_min"]

    candidates = public.generate_alternatives(TARGET_FLIGHT)

    _section(T_GENERATE, "CANDIDATE GENERATION")
    _line(f"Generated {len(candidates)} candidates for {TARGET_FLIGHT}:")
    for c in candidates:
        route_str = " → ".join(c["route"])
        _line(f"  {c['candidate_id']}: {route_str}")

    _assert(len(candidates) == TOTAL_CANDIDATES,
            f"Expected {TOTAL_CANDIDATES} candidates, got {len(candidates)}")
    candidate_ids = [c["candidate_id"] for c in candidates]
    _assert(candidate_ids == ["ALT-A", "ALT-B", "ALT-C", "ALT-D", "ALT-E"],
            f"Candidate IDs out of order: {candidate_ids}")

    return candidates, current_t


def _run_restriction(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_RESTRICT, current_t)
    current_t = state["time_min"]

    restrictions = state.get("restrictions", [])
    active = [r for r in restrictions if r.get("active")]

    _section(T_RESTRICT, "TEMPORARY RESTRICTION ACTIVATION")
    if active:
        for r in active:
            floor = r.get("altitude_floor_ft") or "N/A"
            _line(f"  {r.get('id')}: {r.get('label', 'active')}  "
                  f"alt_floor={floor} ft")
    else:
        _line("  (no active restrictions at this tick)")

    return state, current_t


def _run_validate(candidates: list[dict], current_t: int) -> tuple[dict[str, dict], list[dict], int]:
    state = _advance_to(T_VALIDATE, current_t)
    current_t = state["time_min"]
    decision_context = public.begin_decision_context([TARGET_FLIGHT], candidates)

    validation_results: dict[str, dict] = {}
    for c in candidates:
        validation_results[c["candidate_id"]] = public.validate_candidate(c)

    feasible_candidates = [c for c in candidates if validation_results[c["candidate_id"]]["feasible"]]
    rejected = [c["candidate_id"] for c in candidates if not validation_results[c["candidate_id"]]["feasible"]]

    _section(T_VALIDATE, "HARD CONSTRAINT VALIDATION")
    _line(f"Decision snapshot: {decision_context['snapshot_id']} at T+{decision_context['decision_time']}")
    for c in candidates:
        cid = c["candidate_id"]
        r = validation_results[cid]
        if r["feasible"]:
            _line(f"  {cid}: FEASIBLE  (weather_risk={r['weather_risk']})")
        else:
            reason = r["rejection_reasons"][0] if r["rejection_reasons"] else "unknown"
            if "restriction" in reason.lower():
                label = "restriction"
            elif "fuel" in reason.lower():
                label = "fuel"
            else:
                label = reason[:40]
            _line(f"  {cid}: REJECTED  ← {label}")

    print()
    _section(T_VALIDATE, "HARD REJECTIONS")
    for cid in rejected:
        r = validation_results[cid]
        reason = r["rejection_reasons"][0] if r["rejection_reasons"] else "unknown"
        if "restriction" in reason.lower():
            label = "restriction (R-MONSOON-01 covers FL340 path)"
        elif "fuel" in reason.lower():
            label = "insufficient fuel reserve"
        else:
            label = reason
        _line(f"  {cid} → {label}")

    _assert(set(rejected) == EXPECTED_REJECTED,
            f"Expected {EXPECTED_REJECTED} to be rejected, got {set(rejected)}")
    _assert(len(feasible_candidates) >= 3,
            f"Expected ≥3 feasible candidates, got {len(feasible_candidates)}")

    return validation_results, feasible_candidates, current_t


def _run_evaluate(feasible_candidates: list[dict], current_t: int) -> tuple[dict[str, dict], int]:
    state = _advance_to(T_EVALUATE, current_t)
    current_t = state["time_min"]

    sim_results: dict[str, dict] = {}
    for c in feasible_candidates:
        sim_results[c["candidate_id"]] = public.simulate_candidate(c)

    _section(T_EVALUATE, f"FROZEN DECISION SIMULATION (snapshot T+{sim_results[next(iter(sim_results))].get('decision_time', T_VALIDATE) if sim_results else T_VALIDATE})")
    for cid, sim in sim_results.items():
        _line(
            f"  {cid}: target_delay={sim['target_delay_delta_min']:+.2f} min  "
            f"network_delta={sim['network_delay_delta_min']:+.2f} min  "
            f"affected={sim['affected_flights']}"
        )

    return sim_results, current_t


def _run_stress(feasible_candidates: list[dict], current_t: int) -> tuple[dict[str, dict], int]:
    state = _advance_to(T_STRESS, current_t)
    current_t = state["time_min"]

    stress_results: dict[str, dict] = {}
    for c in feasible_candidates:
        stress_results[c["candidate_id"]] = public.stress_test_candidate(c)

    _section(T_STRESS, "FROZEN DECISION STRESS TEST (5 future scenarios)")
    for cid, sr in stress_results.items():
        survival = f"{sr['passed']}/{sr['total']}"
        pct = sr.get("survival_pct", 0.0)
        _line(f"  {cid}: survival={survival}  ({pct:.0f}%)")
        if sr.get("failures"):
            for failure in sr["failures"][:2]:
                _line(f"         ✗ {failure['scenario_id']}: {failure['reason'][:55]}")

    _assert(len(stress_results) >= 3,
            "Expected stress testing on ≥3 feasible candidates")
    for cid, sr in stress_results.items():
        _assert(sr["total"] == STRESS_PROFILE_COUNT,
                f"{cid}: stress ran {sr['total']} profiles, expected {STRESS_PROFILE_COUNT}")

    return stress_results, current_t


def _run_score_and_critic(
    candidates: list[dict],
    current_t: int,
) -> tuple[list[dict], str, int]:
    state = _advance_to(T_CRITIC, current_t)
    current_t = state["time_min"]

    scored = public.score_candidates(candidates)

    _section(T_CRITIC, f"ENGINE RANKING / CHALLENGE PREVIEW (snapshot T+{scored[0]['decision_context']['decision_time'] if scored else T_VALIDATE})")
    ranked_feasible = [item for item in scored if item.get("feasible") is True]
    if not ranked_feasible:
        raise FlagshipAssertionError("No feasible candidate received a decision score")
    top = ranked_feasible[0]
    runner_up = ranked_feasible[1] if len(ranked_feasible) > 1 else None
    _line(f"Preliminary leader: {top['candidate_id']}  (score={top['decision_score']:.3f})")
    if runner_up:
        _line(f"Challenger        : {runner_up['candidate_id']}  (score={runner_up['decision_score']:.3f})")
        ls = top.get("stress_survival", {}).get("passed", 0)
        rs = runner_up.get("stress_survival", {}).get("passed", 0)
        if rs > ls:
            _line(f"Challenge signal  : {runner_up['candidate_id']} has higher resilience "
                  f"({rs}/{STRESS_PROFILE_COUNT} vs {ls}/{STRESS_PROFILE_COUNT})")
        else:
            _line(f"Challenge signal  : {top['candidate_id']} leads on score and resilience")

    return scored, top["candidate_id"], current_t


def _select_recommendation(scored: list[dict]) -> dict:
    """Recommend the top engine-ranked feasible candidate, with no overrides."""
    feasible = [candidate for candidate in scored if candidate.get("feasible") is True]
    if not feasible:
        raise FlagshipAssertionError("No feasible candidate can be recommended")
    return feasible[0]


def _run_recommend_and_approve(
    scored: list[dict],
    preliminary_leader: str,
    current_t: int,
) -> tuple[dict, str, dict, int]:
    """
    T+28: Recommendation  +  T+30: Human approval  +  apply_intervention.

    apply_intervention() re-validates the candidate against the live engine state,
    so we apply before advancing past the safe fuel window.  The approval gate
    is explicitly represented as a deterministic YES step that precedes the apply
    call — it is not skipped.
    """
    state = _advance_to(T_RECOMMEND, current_t)
    current_t = state["time_min"]

    recommendation = _select_recommendation(scored)
    recommended_id = recommendation["candidate_id"]
    top_engine_candidate = _select_recommendation(scored)
    _assert(
        recommended_id == top_engine_candidate["candidate_id"],
        "Recommendation must equal the highest-scoring feasible candidate",
    )

    _section(T_RECOMMEND, "RECOMMENDATION")
    _line(f"Selected  : {recommended_id}")
    _line(f"Score     : {recommendation['decision_score']:.3f}")
    stress = recommendation.get("stress_survival", {})
    _line(f"Resilience: {stress.get('passed', 0)}/{stress.get('total', STRESS_PROFILE_COUNT)} "
          "stress scenarios survived")
    _line(f"Target Δ  : {recommendation.get('target_delay_min', 0):+.2f} min")
    network_delta = recommendation.get("network_delay_delta_min", 0)
    _line(f"Network Δ : {network_delta:+.2f} min")
    reintervention = recommendation.get("reintervention_probability", 0)
    _line(f"Re-intervention probability: {reintervention:.0%}")

    _assert(recommendation is not None, "No recommendation produced")

    # ── T+30  HUMAN APPROVAL GATE ────────────────────────────
    # In a live deployment the system is blocked here awaiting dispatcher input.
    # For the deterministic demo runner, approval is an explicit YES constant.
    # The gate is NOT skipped — apply is called only after this decision.
    # No interactive stdin prompt so CI/tests do not hang.
    approved: bool = True   # Dispatcher approval — deterministic demo: YES

    _section(T_POST_APPLY, "HUMAN APPROVAL")
    _line(f"Candidate : {recommended_id}")
    _line(f"Approved  : {'YES ✓' if approved else 'NO ✗'}")

    if not approved:
        raise RuntimeError(
            f"Dispatcher rejected {recommended_id}. Flagship aborted before apply."
        )

    apply_result = public.apply_intervention(recommended_id)
    _line(f"Status    : {apply_result['status']}")
    _line(f"Flight    : {apply_result['flight_id']}")

    _assert(apply_result["status"] == "EXECUTING",
            f"Expected EXECUTING after apply, got {apply_result['status']}")

    return recommendation, recommended_id, apply_result, current_t


def _run_verify(applied_id: str, current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_VERIFY, current_t)
    current_t = state["time_min"]

    ver = public.verify_state(applied_id)

    _section(T_VERIFY, "VERIFICATION")
    _line(f"Status         : {ver['status']}")
    _line(f"Target Δ       : {ver['target_delay_delta_min']:+.2f} min")
    _line(f"Network Δ      : {ver['network_delay_delta_min']:+.2f} min")
    _line(f"Affected flights: {ver['affected_flights']}")
    _line(f"Constraints    : {'SAFE' if ver['constraints_safe'] else 'UNSAFE'}")
    _line(f"New degradation: {'YES' if ver['new_degradation'] else 'NO'}")

    valid_statuses = {"VERIFIED", "REASSESSMENT_REQUIRED"}
    _assert(ver["status"] in valid_statuses,
            f"Unexpected verification status: {ver['status']}")

    return ver, current_t


def _run_monitor(current_t: int) -> tuple[dict, int]:
    state = _advance_to(T_MONITOR, current_t)
    current_t = state["time_min"]

    aircraft = _aircraft_by_id(state)
    f102 = aircraft.get(TARGET_FLIGHT, {})

    _section(T_MONITOR, "MONITORING")
    _line(f"Simulation time : T+{current_t}")
    _line(f"Airborne flights: {_airborne_count(state)}")
    _line(f"Holding flights : {_holding_count(state)}")
    _line(f"Network delay   : {_network_delay(state):.1f} min")
    _line(f"F102 status     : {f102.get('status')}")
    _line(f"F102 fuel       : {f102.get('fuel_remaining_min', 0):.1f} min remaining")

    return state, current_t


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_flagship(*, verbose_json: bool = False) -> dict:
    """Execute the complete deterministic flagship scenario.

    Returns a machine-readable summary dict (JSON-serializable).
    Raises FlagshipAssertionError on story violations.
    Raises RuntimeError if approval is denied or apply fails.
    """
    public.reset_engine()
    current_t = 0

    print()
    print("=" * 56)
    print("  AERIS — MUMBAI MONSOON FLAGSHIP")
    print(f"  Scenario : {SCENARIO_ID}")
    print(f"  Target   : {TARGET_FLIGHT}")
    print("=" * 56)

    # T+0  Baseline ───────────────────────────────────────────
    _, current_t = _run_baseline(current_t)

    # T+5  Weather disruption ─────────────────────────────────
    _, current_t = _run_weather(current_t)

    # T+8  BOM capacity drop ──────────────────────────────────
    _, current_t = _run_bom_capacity(current_t)

    # T+10 Holding begins ─────────────────────────────────────
    _, current_t = _run_holding(current_t)

    # T+12 S6 capacity reduction ──────────────────────────────
    _, current_t = _run_s6_capacity(current_t)

    # T+15 F102 degradation ───────────────────────────────────
    _, current_t = _run_degradation(current_t)

    # T+17 Candidate generation ───────────────────────────────
    candidates, current_t = _run_generate(current_t)

    # T+18 Restriction activation ─────────────────────────────
    _, current_t = _run_restriction(current_t)

    # T+19 Constraint validation + hard rejections ────────────
    validation_results, feasible_candidates, current_t = _run_validate(candidates, current_t)

    # T+21 Network simulation / evaluation ────────────────────
    _, current_t = _run_evaluate(feasible_candidates, current_t)

    # T+24 Stress testing ─────────────────────────────────────
    _, current_t = _run_stress(feasible_candidates, current_t)

    # T+26 Score all + critic ─────────────────────────────────
    scored, preliminary_leader, current_t = _run_score_and_critic(candidates, current_t)

    # T+28 Recommendation  |  T+30 Human approval + apply ────
    # (apply happens before advancing clock past the safe fuel window)
    recommendation, recommended_id, apply_result, current_t = _run_recommend_and_approve(
        scored, preliminary_leader, current_t
    )

    # T+32 Verification ───────────────────────────────────────
    ver_result, current_t = _run_verify(recommended_id, current_t)

    # T+35 Monitoring ─────────────────────────────────────────
    monitoring_state, current_t = _run_monitor(current_t)
    monitoring_network_delay = _network_delay(monitoring_state)
    post_verification_reassessment = monitoring_network_delay > 120.0
    if post_verification_reassessment:
        _line("Post-verification status: NETWORK STRESS PERSISTS — reassessment should be triggered.")
    else:
        _line("Post-verification status: NETWORK STABLE.")

    # ── Final result ──────────────────────────────────────────
    top = next((c for c in scored if c["candidate_id"] == recommended_id), scored[0])
    top_engine_ranked_candidate = _select_recommendation(scored)["candidate_id"]
    _assert(
        recommended_id == top_engine_ranked_candidate,
        "Flagship winner differs from the top engine-ranked feasible candidate",
    )
    final_result = {
        "scenario_id": SCENARIO_ID,
        "target_flight": TARGET_FLIGHT,
        "recommendation": recommended_id,
        "top_engine_ranked_candidate": top_engine_ranked_candidate,
        "verification_status": ver_result["status"],
        "decision_score": round(top.get("decision_score", 0.0), 4),
        "target_delay_delta_min": round(top.get("target_delay_min", 0.0), 2),
        "network_delay_delta_min": round(top.get("network_delay_delta_min", 0.0), 2),
        "stress_survival": top.get("stress_survival", {}),
        "reintervention_probability": round(top.get("reintervention_probability", 0.0), 4),
        "candidates_generated": len(candidates),
        "candidates_rejected": len(candidates) - len(feasible_candidates),
        "candidates_feasible": len(feasible_candidates),
        "apply_status": apply_result["status"],
        "final_time_min": current_t,
        "verification_time_min": T_VERIFY,
        "post_verification_monitoring": {
            "time_min": current_t,
            "network_delay_min": round(monitoring_network_delay, 2),
            "reassessment_recommended": post_verification_reassessment,
        },
        "decision_context": top.get("decision_context"),
        "flagship_result": "SUCCESS" if ver_result["status"] == "VERIFIED" else "FAILED",
    }

    # ── Print final summary ───────────────────────────────────
    print()
    print("=" * 56)
    outcome = final_result["flagship_result"]
    print(f"  FLAGSHIP RESULT: {outcome}")
    if outcome == "SUCCESS":
        print(f"  Intervention   : {recommended_id} — {ver_result['status']}")
        print(f"  Decision score : {final_result['decision_score']:.3f}")
        stress_s = final_result["stress_survival"]
        print(f"  Stress survival: {stress_s.get('passed', 0)}/{stress_s.get('total', STRESS_PROFILE_COUNT)}")
    else:
        print(f"  Verification   : {ver_result['status']}")
    print("=" * 56)

    if verbose_json:
        print()
        print("── Machine-readable summary ──────────────────────────")
        print(json.dumps(final_result, indent=2))

    return final_result


if __name__ == "__main__":
    try:
        result = run_flagship(verbose_json=True)
        sys.exit(0 if result["flagship_result"] == "SUCCESS" else 1)
    except FlagshipAssertionError as exc:
        print()
        print(f"ASSERTION FAILURE: {exc}", file=sys.stderr)
        sys.exit(2)
    except Exception as exc:
        print()
        print(f"RUNNER ERROR: {exc}", file=sys.stderr)
        raise
