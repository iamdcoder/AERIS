import test from "node:test";
import assert from "node:assert/strict";

import { buildTimeline, normalizeAgentState } from "./dashboardAdapter.js";

test("timeline uses event simulation time instead of a hard-coded recommendation time", () => {
  const state = {
    stage: "HUMAN_APPROVAL",
    recommendation: { candidate_id: "ALT-D" },
    events: [
      {
        event_type: "RECOMMENDATION_READY",
        data: { simulation_time_min: 27 },
      },
      {
        event_type: "APPROVAL_RESULT",
        data: { simulation_time_min: 29 },
      },
    ],
  };

  const timeline = buildTimeline(state, 35, null);
  const recommendation = timeline.find((item) => item.title === "AERIS recommends");
  const approval = timeline.find((item) => item.title === "Human approves");

  assert.equal(recommendation?.time, "T+27");
  assert.equal(approval, undefined);

  const approvedState = {
    ...state,
    approval: { decision: "APPROVED" },
  };
  const approvedTimeline = buildTimeline(approvedState, 35, null);
  const approvedEvent = approvedTimeline.find((item) => item.title === "Human approves");
  assert.equal(approvedEvent?.time, "T+29");
});

test("degraded reassessment timeline records rejection without inventing a fallback recommendation", () => {
  const state = {
    stage: "DEGRADED",
    recommendation: null,
    approval: { decision: "REJECTED" },
    events: [
      {
        event_type: "REASSESSMENT_COMPLETE",
        data: {
          simulation_time_min: 33,
          rejected_candidate_id: "ALT-D",
          rejection_reason: "Dispatcher rejected the recommendation.",
          new_recommended_candidate_id: null,
        },
      },
      {
        event_type: "NO_ROBUST_INTERVENTION",
        data: { simulation_time_min: 33 },
      },
    ],
  };

  const timeline = buildTimeline(state, 35, {
    rejectedCandidateId: "ALT-D",
    rejectionReason: "Dispatcher rejected the recommendation.",
    newRecommendedCandidateId: null,
  });

  assert.equal(
    timeline.filter((item) => item.title === "No robust intervention").at(-1)?.time,
    "T+33",
  );
});

test("verified agent state normalizes remaining fuel without throwing during approval completion", () => {
  const state = {
    run_id: "run-1",
    target_flight_id: "F102",
    stage: "COMPLETED",
    approval: { decision: "APPROVED" },
    world_state: {
      time_min: 20,
      aircraft: [
        {
          id: "F102",
          origin: "BOM",
          destination: "DEL",
          lat: 19,
          lon: 73,
        },
      ],
      sectors: [],
      weather: [],
      restrictions: [],
      airports: [
        {
          id: "BOM",
          operational_status: "NORMAL",
          arrival_capacity: 10,
          normal_arrival_capacity: 10,
        },
      ],
      network_metrics: {},
    },
    candidates: [],
    verification_result: {
      status: "VERIFIED",
      after_metrics: {
        target_delay_delta_min: 1,
        network_delay_delta_min: 2,
        new_conflicts: 0,
        fuel_margin_kg: 100,
        fuel_reserve_margin_min: 30,
        remaining_fuel_min: 120,
        peak_sector_utilization_pct: 80,
      },
    },
  };

  const dashboard = normalizeAgentState(state);

  assert.equal(dashboard.verification.status, "VERIFIED");
  assert.equal(dashboard.verification.remainingFuelMin, 120);
  assert.equal(dashboard.approvalStatus, "APPROVED");
});
