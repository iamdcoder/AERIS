import { DEMO_DASHBOARD } from "./demoData";

const ROUTES = {
  "ALT-A": ["W3", "W10", "W11", "BOM"],
  "ALT-B": ["W3", "W5", "W6", "W8", "W11", "W12", "BOM"],
  "ALT-C": ["W3", "W5", "W10", "W11", "W12", "BOM"],
  "ALT-D": ["W3", "W5", "W7", "BOM"],
  "ALT-E": ["W3", "W5", "W7", "W9", "W8", "W11", "W12", "BOM"],
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function buildCandidates() {
  return DEMO_DASHBOARD.candidates.map((candidate) => ({
    candidate_id: candidate.id,
    flight_id: "F102",
    intervention_type: candidate.interventionType,
    strategy: candidate.label,
    route: ROUTES[candidate.id] || [],
    feasible: candidate.feasible,
    local_score: candidate.localScore,
    decision_score: candidate.decisionScore,
    target_delay_min: candidate.targetDelayMin,
    network_delay_delta_min: candidate.networkDelayDeltaMin,
    max_sector_utilization_pct: candidate.peakSectorUtilization * 100,
    resilience_score: candidate.resilience,
    fuel_margin_kg: candidate.fuelMarginKg,
    affected_flights: candidate.affectedFlights,
    added_distance_km: candidate.extraDistanceKm,
    stress_survival: {
      passed: candidate.stressSurvival,
      total: candidate.stressTotal,
    },
    rejection_reason: candidate.rejectionReason,
    summary: candidate.summary,
  }));
}

function events(reassessed = false, approved = false) {
  const result = [
    { sequence: 1, stage: "OBSERVE", event_type: "STATE_TRANSITION", message: "Read deterministic airspace state." },
    { sequence: 2, stage: "DIAGNOSE", event_type: "DIAGNOSIS_COMPLETE", message: "Weather, BOM capacity and S5/S6 pressure explain the degradation." },
    { sequence: 3, stage: "PLAN", event_type: "CANDIDATES_GENERATED", message: "Generated five intervention alternatives." },
    { sequence: 4, stage: "EVALUATE", event_type: "ENGINE_RANKING_READY", candidate_id: "ALT-D", message: "Network-aware ranking favors ALT-D after feasibility filtering.", data: { local_vs_global_flip: true } },
    { sequence: 5, stage: "EVALUATE", event_type: "PRELIMINARY_LEADER", candidate_id: "ALT-A", message: "ALT-A is the locally attractive preliminary leader." },
    { sequence: 6, stage: "STRESS_TEST", event_type: "STRESS_TEST_COMPLETE", candidate_id: "ALT-D", message: "ALT-D survives 4/5 future scenarios." },
    { sequence: 7, stage: "CRITIC", event_type: "CRITIC_COMPLETE", candidate_id: "ALT-A", message: "Critic challenges ALT-A on future robustness and re-intervention risk." },
    { sequence: 8, stage: "RECOMMEND", event_type: "RECOMMENDATION_READY", candidate_id: reassessed ? "ALT-A" : "ALT-D", message: reassessed ? "AERIS selected ALT-A as the next candidate after operator rejection." : "AERIS recommends ALT-D as the resilient option." },
  ];

  if (reassessed) {
    result.push({ sequence: 9, stage: "REASSESS", event_type: "REASSESSMENT_COMPLETE", candidate_id: "ALT-A", message: "AERIS reassessed the remaining candidates after operator rejection.", data: {
      rejected_candidate_id: "ALT-D",
      rejection_reason: "Prefer a different operational trade-off.",
      excluded_candidate_ids: ["ALT-D"],
      new_recommended_candidate_id: "ALT-A",
      summary: "AERIS excluded the rejected intervention and generated a fresh recommendation for human review.",
    }});
    return result;
  }

  if (approved) {
    result.push({ sequence: 9, stage: "EXECUTE", event_type: "INTERVENTION_EXECUTED", candidate_id: "ALT-D", message: "Approved intervention applied inside the simulation." });
    result.push({ sequence: 10, stage: "VERIFY", event_type: "VERIFICATION_COMPLETE", candidate_id: "ALT-D", message: "Post-action constraints and network state verified." });
  }

  return result;
}

function baseState() {
  const dashboard = clone(DEMO_DASHBOARD);
  dashboard.scenarioId = "mumbai_weather_crisis_v2";
  dashboard.simulationTimeMin = 19;
  return {
    run_id: `OFFLINE-${Date.now()}`,
    scenario_id: dashboard.scenarioId,
    target_flight_id: "F102",
    stage: "HUMAN_APPROVAL",
    status: "WAITING_HUMAN",
    step: 8,
    world_state: {
      time_min: 19,
      scenario_id: dashboard.scenarioId,
      target_flight: {
        id: "F102", callsign: "AI102", origin: "DEL", destination: "BOM",
        status: "DEGRADED", fuel_remaining_min: 50, reserve_required_min: 12, delay_min: 2.6, performance_class: "A320", route: ["W3", "W10", "W11", "BOM"],
      },
      aircraft: [],
      sectors: dashboard.sectors,
      weather_cells: [{ id: "WX-BOM-01", type: "CONVECTIVE", severity: "HIGH", uncertainty: 0.25 }],
      disruptions: dashboard.disruption,
    },
    candidates: buildCandidates(),
    feasible_candidates: buildCandidates().filter((c) => c.feasible),
    simulation_results: [],
    stress_test_results: [],
    leading_candidate_id: "ALT-D",
    critic_result: {
      candidate_id: "ALT-A",
      challenged: true,
      severity: "HIGH",
      finding: "ALT-A is locally attractive but fails the resilience challenge; ALT-D is the stronger surviving option.",
      trigger_conditions: ["Weather expansion +20%", "Traffic demand increase", "Sector capacity reduction"],
      evidence_ids: ["EVID-CRITIC-01"],
    },
    recommendation: {
      candidate_id: "ALT-D",
      confidence: 0.91,
      summary: DEMO_DASHBOARD.recommendation.summary,
      why_selected: [
        "Lowest network ripple among feasible reroutes.",
        "Best future robustness across tested scenarios.",
        "Preserves a safe fuel margin.",
      ],
      rejected_candidates: [
        { candidate_id: "ALT-A", reason: "Higher network ripple and poor stress survival." },
        { candidate_id: "ALT-C", reason: "Hard constraint violation from the active restriction." },
        { candidate_id: "ALT-E", reason: "Fuel margin below the minimum reserve." },
      ],
      critic: {
        candidate_id: "ALT-A", challenged: true, severity: "HIGH", finding: "ALT-A is locally attractive but fails the resilience challenge; ALT-D is the stronger surviving option."
      },
      evidence_ids: ["EVID-NETWORK-01", "EVID-STRESS-01", "EVID-CRITIC-01"],
      human_approval_required: true,
    },
    approval: { required: true, status: "AWAITING_APPROVAL", decision: null, reason: null },
    verification_result: null,
    errors: [],
    events: events(),
    evidence: [
      { evidence_id: "EVID-NETWORK-01", kind: "SIMULATION", title: "Network impact", summary: "ALT-D produces the smallest network ripple among the feasible candidates.", data: { network_delay_delta_min: -14, affected_flights: 1 } },
      { evidence_id: "EVID-STRESS-01", kind: "STRESS_TEST", title: "Future robustness", summary: "ALT-D survives 4/5 modeled futures in the offline presentation path.", data: { passed: 4, total: 5 } },
      { evidence_id: "EVID-CRITIC-01", kind: "CRITIC", title: "Adversarial review", summary: "ALT-A is challenged because its apparent local advantage creates network vulnerability.", data: { challenged: true, challenge_severity: "HIGH", failure_modes_checked: ["WORSENING_WEATHER", "REDUCED_SECTOR_CAPACITY", "INCREASED_TRAFFIC"], replacement_candidate_id: "ALT-D" } },
    ],
  };
}

export function createOfflineAgentState() {
  return baseState();
}

export function approveOfflineRun(state) {
  const next = clone(state);
  next.stage = "COMPLETE";
  next.status = "COMPLETED";
  next.step = 10;
  next.approval = { required: true, status: "APPROVED", decision: "APPROVED", reason: null };
  next.events = events(false, true);
  next.verification_result = {
    status: "VERIFIED", verified_at_min: 32,
    target_delay_delta_min: -0.60,
    network_delay_delta_min: -14.0,
    new_conflicts: 0,
    fuel_margin_kg: 610,
    fuel_reserve_margin_min: 13.38,
    after_metrics: { target_delay_delta_min: -0.60, network_delay_delta_min: -14.0, new_conflicts: 0, fuel_margin_kg: 610, fuel_reserve_margin_min: 13.38, peak_sector_utilization_pct: 82 },
  };
  return next;
}

export function rejectOfflineRun(state, reason) {
  const next = clone(state);
  next.stage = "HUMAN_APPROVAL";
  next.status = "WAITING_HUMAN";
  next.step = 9;
  next.leading_candidate_id = "ALT-A";
  next.recommendation = { ...next.recommendation, candidate_id: "ALT-A", confidence: 0.78, summary: "AERIS reassessed the remaining candidates after the operator rejected ALT-D.", why_selected: ["ALT-D was excluded by the operator.", "ALT-A is the next available candidate in the deterministic ranking.", "Fresh human approval is required before any execution."] };
  next.approval = { required: true, status: "AWAITING_APPROVAL", decision: "REJECTED", reason };
  next.events = events(true, false);
  return next;
}
