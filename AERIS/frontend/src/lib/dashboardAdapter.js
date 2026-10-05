import { DEMO_TIMELINE } from "./demoData.js";


function asNumber(
  value,
  fallback = null,
) {
  const parsed =
    Number(value);

  return Number.isFinite(parsed)
    ? parsed
    : fallback;
}


function asPercentRatio(
  value,
) {
  const number =
    asNumber(value);

  if (number === null) {
    return null;
  }

  if (number > 2) {
    return number / 100;
  }

  return number;
}


function asArray(
  value,
) {
  if (Array.isArray(value)) {
    return value;
  }

  if (
    value &&
    typeof value === "object"
  ) {
    return Object.values(value);
  }

  return [];
}


function unwrapObject(
  value,
  keys = [],
) {
  if (
    !value ||
    typeof value !== "object"
  ) {
    return null;
  }

  for (const key of keys) {
    if (
      value[key] &&
      typeof value[key] === "object"
    ) {
      return value[key];
    }
  }

  return value;
}


function findTargetFlight(
  worldState,
  flightId,
) {
  if (
    worldState?.target_flight
  ) {
    return worldState.target_flight;
  }

  if (
    worldState?.target?.flight
  ) {
    return worldState.target.flight;
  }

  if (
    worldState?.target?.id
  ) {
    return worldState.target;
  }

  const aircraft =
    asArray(
      worldState?.aircraft,
    );

  return (
    aircraft.find(
      (flight) =>
        String(
          flight?.id || "",
        ) ===
        String(
          flightId || "F102",
        ),
    ) || null
  );
}


function normalizeFlight(
  flight,
  fallbackId = "F102",
) {
  const value =
    unwrapObject(
      flight,
      [
        "flight",
        "aircraft",
      ],
    );

  if (!value) {
    return {
      id: fallbackId,
      callsign: fallbackId,
      origin: "DEL",
      destination: "BOM",
      status: "UNKNOWN",
      fuelRemainingMin: 0,
      reserveRequiredMin: 12,
      currentDelayMin: 0,
      performanceClass: "UNKNOWN",
      position: null,
      altitudeFt: null,
      speedKt: null,
      route: [],
    };
  }

  const route =
    asArray(
      value.route,
    );

  return {
    id:
      value.id ||
      fallbackId,

    callsign:
      value.callsign ||
      value.id ||
      fallbackId,

    origin:
      value.origin ||
      route[0] ||
      "DEL",

    destination:
      value.destination ||
      route[
        route.length - 1
      ] ||
      "BOM",

    status:
      value.status ||
      "UNKNOWN",

    fuelRemainingMin:
      asNumber(
        value.fuel_remaining_min,
        0,
      ),

    reserveRequiredMin:
      asNumber(
        value.reserve_required_min ??
          value.required_reserve_min,
        12,
      ),

    currentDelayMin:
      asNumber(
        value.delay_min ??
          value.current_delay_min,
        0,
      ),

    performanceClass:
      value.performance_class ||
      "UNKNOWN",

    position:
      value.position ||
      null,

    altitudeFt:
      asNumber(
        value.altitude_ft,
      ),

    speedKt:
      asNumber(
        value.speed_kt,
      ),

    route,
  };
}


function deriveLocalScore(
  candidate,
) {
  const targetDelay =
    asNumber(
      candidate?.target_delay_min,
    );

  const distance =
    asNumber(
      candidate?.added_distance_km,
    );

  if (
    targetDelay === null &&
    distance === null
  ) {
    return null;
  }

  const targetBenefit =
    targetDelay === null
      ? 0.5
      : Math.max(
          0,
          Math.min(
            1,
            1 -
              targetDelay /
                20,
          ),
        );

  const distanceEfficiency =
    distance === null
      ? 0.5
      : Math.max(
          0,
          Math.min(
            1,
            1 -
              distance /
                250,
          ),
        );

  return Number(
    (
      targetBenefit *
        0.70 +
      distanceEfficiency *
        0.30
    ).toFixed(
      2,
    ),
  );
}


function normalizeCandidate(
  candidate,
) {
  const value =
    candidate || {};

  const stress =
    value.stress_survival;

  let stressPassed = 0;
  let stressTotal = 0;

  if (
    stress &&
    typeof stress === "object"
  ) {
    stressPassed =
      asNumber(
        stress.passed,
        0,
      );

    stressTotal =
      asNumber(
        stress.total,
        0,
      );
  } else if (
    typeof stress === "string"
  ) {
    const match =
      stress.match(
        /(\d+)\s*\/\s*(\d+)/,
      );

    if (match) {
      stressPassed =
        Number(
          match[1],
        );

      stressTotal =
        Number(
          match[2],
        );
    }
  }

  const resilience =
    asNumber(
      value.resilience_score,
      asNumber(
        value.resilience_metrics
          ?.future_robustness,
        0,
      ),
    ) ?? 0;

  const peak =
    asPercentRatio(
      value.max_sector_utilization_pct ??
        value.peak_sector_utilization,
    );

  const strategy =
    value.strategy ||
    value.intervention_type ||
    "INTERVENTION";

  const readableStrategy =
    String(
      strategy,
    )
      .replaceAll(
        "_",
        " ",
      )
      .replaceAll(
        "-",
        " ",
      )
      .toUpperCase();

  const rejectionReasons =
    Array.isArray(
      value.rejection_reasons,
    )
      ? value.rejection_reasons
      : [];

  const explanation =
    value.score_explanation ||
    value.explanation ||
    (
      rejectionReasons.length
        ? rejectionReasons.join(
            "; ",
          )
        : `${readableStrategy} candidate evaluated by the deterministic engine.`
    );

  return {
    id:
      value.candidate_id ||
      value.id ||
      "UNKNOWN",

    interventionType:
      readableStrategy,

    feasible:
      value.feasible === true,

    recommendable:
      value.recommendable !== false &&
      value.recommendable !== 0,

    recommendationBlockers:
      Array.isArray(value.recommendation_blockers)
        ? value.recommendation_blockers
        : [],

    operatorRejected:
      false,

    localScore:
      asNumber(
        value.local_score,
        deriveLocalScore(
          value,
        ),
      ),

    decisionScore:
      asNumber(
        value.decision_score,
      ),

    targetDelayMin:
      asNumber(
        value.target_delay_min,
      ),

    networkDelayDeltaMin:
      asNumber(
        value.network_delay_delta_min,
      ),

    peakSectorUtilization:
      peak,

    resilience,

    stressSurvival:
      stressPassed,

    stressTotal,

    affectedFlights:
      asNumber(
        value.affected_flights,
      ),

    fuelMarginKg:
      asNumber(
        value.fuel_margin_kg,
      ),

    fuelMarginMin:
      asNumber(
        value.fuel_reserve_margin_min,
      ),

    extraDistanceKm:
      asNumber(
        value.added_distance_km,
      ),

    label:
      value.label ||
      readableStrategy,

    summary:
      explanation,

    rejectionReason:
      rejectionReasons.length
        ? rejectionReasons.join(
            "; ",
          )
        : value.route_validation_error ||
          null,

    raw: value,
  };
}


function pushAlert(
  alerts,
  alert,
) {
  if (!alert?.type) {
    return;
  }

  const duplicate =
    alerts.some(
      (existing) =>
        existing.type ===
          alert.type &&
        existing.summary ===
          alert.summary,
    );

  if (!duplicate) {
    alerts.push(
      alert,
    );
  }
}


function deriveDisruptions(
  worldState,
  response,
) {
  const alerts = [];

  for (
    const item of asArray(
      worldState?.alerts,
    )
  ) {
    pushAlert(
      alerts,
      {
        type: item.type,
        severity:
          item.severity ||
          "HIGH",
        summary:
          item.summary ||
          "Active disruption detected.",
      },
    );
  }

  const disruptionResponse =
    response ||
    worldState?.disruptions ||
    {};

  for (
    const cell of asArray(
      disruptionResponse.weather_cells ??
        worldState?.weather_cells,
    )
  ) {
    const intensity =
      String(
        cell?.intensity ||
          cell?.severity ||
          "NORMAL",
      ).toUpperCase();

    if (
      ![
        "NORMAL",
        "LOW",
        "NONE",
      ].includes(
        intensity,
      )
    ) {
      pushAlert(
        alerts,
        {
          type:
            "WEATHER_EXPANSION",

          severity:
            intensity ===
            "MODERATE"
              ? "HIGH"
              : intensity,

          summary:
            `Weather cell ${
              cell?.id ||
              "UNKNOWN"
            } is ${
              intensity.toLowerCase()
            } and constrains the operational corridor.`,
        },
      );
    }
  }

  for (
    const restriction of asArray(
      disruptionResponse.restrictions ??
        worldState?.restrictions,
    )
  ) {
    if (
      restriction?.active ===
      true
    ) {
      pushAlert(
        alerts,
        {
          type:
            "AIRSPACE_RESTRICTION",

          severity:
            "HIGH",

          summary:
            `${
              restriction.id ||
              "Active restriction"
            } is constraining routing.`,
        },
      );
    }
  }

  return alerts;
}


function sectorUtilization(
  sector,
) {
  const direct =
    asPercentRatio(
      sector?.utilization_pct ??
        sector?.projected_utilization,
    );

  const forecast =
    asNumber(
      sector?.forecast_traffic,
    );

  const capacity =
    asNumber(
      sector?.capacity,
    );

  const forecastRatio =
    forecast !== null &&
    capacity !== null &&
    capacity > 0
      ? forecast /
        capacity
      : null;

  if (
    direct === null &&
    forecastRatio === null
  ) {
    return null;
  }

  if (
    direct === null
  ) {
    return forecastRatio;
  }

  if (
    forecastRatio ===
    null
  ) {
    return direct;
  }

  return Math.max(
    direct,
    forecastRatio,
  );
}


function normalizeNetwork(
  worldState,
  networkResponse,
) {
  const aircraft =
    asArray(
      worldState?.aircraft,
    );

  const sectors =
    asArray(
      worldState?.sectors,
    );

  const totalDelay =
    aircraft.reduce(
      (
        total,
        flight,
      ) =>
        total +
        (
          asNumber(
            flight?.delay_min,
            0,
          ) || 0
        ),
      0,
    );

  const holding =
    aircraft.filter(
      (flight) =>
        [
          "HOLDING",
          "HELD",
        ].includes(
          String(
            flight?.status ||
              "",
          ).toUpperCase(),
        ),
    ).length;

  const stressed =
    sectors.filter(
      (sector) => {
        const status =
          String(
            sector?.status ||
              "",
          ).toUpperCase();

        const utilization =
          sectorUtilization(
            sector,
          );

        return (
          [
            "STRESSED",
            "CONGESTED",
            "OVERLOADED",
            "CRITICAL",
          ].includes(
            status,
          ) ||
          (
            utilization !==
              null &&
            utilization >=
              0.85
          )
        );
      },
    ).length;

  return {
    activeAircraft:
      asNumber(
        networkResponse?.total_flights ??
          networkResponse?.airborne_flights,
        aircraft.length,
      ),

    aircraftInHolding:
      asNumber(
        networkResponse?.holding_flights,
        holding,
      ),

    stressedSectors:
      stressed,

    networkDelayMin:
      asNumber(
        networkResponse?.total_delay_min,
        totalDelay,
      ),
  };
}


function normalizeAirport(
  worldState,
  flight,
) {
  const destination =
    flight?.destination ||
    "BOM";

  const airports =
    asArray(
      worldState?.airports,
    );

  const airport =
    airports.find(
      (item) =>
        item?.id ===
        destination,
    ) ||
    airports.find(
      (item) =>
        item?.id ===
        "BOM",
    ) ||
    airports[0];

  if (!airport) {
    return {
      id: destination,
      operationalStatus:
        "UNKNOWN",
      arrivalCapacityPer15Min:
        null,
      normalArrivalCapacityPer15Min:
        null,
    };
  }

  return {
    id:
      airport.id ||
      destination,

    operationalStatus:
      airport.operational_status ||
      "NORMAL",

    arrivalCapacityPer15Min:
      asNumber(
        airport.arrival_capacity,
      ),

    normalArrivalCapacityPer15Min:
      asNumber(
        airport.normal_arrival_capacity,
      ),
  };
}


function normalizeVerification(
  agentState,
  recommendedCandidate,
) {
  const value =
    agentState?.verification_result;

  if (!value) {
    return {
      status: "PENDING",
      targetDelayDeltaMin:
        null,
      networkDelayDeltaMin:
        null,
      peakSectorUtilization:
        null,
      newConflicts:
        null,
      fuelMarginKg:
        null,
      fuelMarginMin:
        recommendedCandidate?.fuelMarginMin ??
        null,
      remainingFuelMin:
        null,
      downstreamRisk:
        "UNKNOWN",
      constraintsSafe:
        null,
      routeValid:
        null,
      conflictSafe:
        null,
      restrictionSafe:
        null,
      checksAvailable:
        false,
      verifiedAtMin:
        null,
      summary:
        "Post-action verification has not run yet.",
    };
  }

  const after =
    value.after_metrics ||
    {};

  const targetDelay =
    asNumber(
      after.target_delay_delta_min ??
        value.target_delay_delta_min,
    );

  const networkDelay =
    asNumber(
      after.network_delay_delta_min ??
        value.network_delay_delta_min,
    );

  const conflicts =
    asNumber(
      after.new_conflicts ??
        value.new_conflicts,
    );

  const fuelMarginKg =
    asNumber(
      after.fuel_margin_kg ??
        value.fuel_margin_kg,
    );

  const fuelMarginMin =
    asNumber(
      after.fuel_reserve_margin_min ??
        value.fuel_reserve_margin_min,
    ) ??
    recommendedCandidate?.fuelMarginMin ??
    null;

  const remainingFuel =
    asNumber(
      after.remaining_fuel_min ??
        value.remaining_fuel_min,
    );

  const peak =
    asPercentRatio(
      after.max_sector_utilization_pct ??
        after.peak_sector_utilization ??
        value.max_sector_utilization_pct ??
        value.peak_sector_utilization,
    );

  const constraintsSafe =
    typeof value.constraints_safe ===
    "boolean"
      ? value.constraints_safe
      : typeof after.constraints_safe ===
          "boolean"
        ? after.constraints_safe
        : null;

  const routeValid =
    typeof value.route_valid ===
    "boolean"
      ? value.route_valid
      : null;

  const conflictSafe =
    typeof value.conflict_safe ===
    "boolean"
      ? value.conflict_safe
      : null;

  const restrictionSafe =
    typeof value.restriction_safe ===
    "boolean"
      ? value.restriction_safe
      : null;

  const downstreamRisk =
    value.downstream_risk ||
    after.downstream_risk ||
    "UNKNOWN";

  const verifiedAtMin =
    asNumber(
      after.verified_at_min ??
        value.verified_at_min,
    );

  return {
    status:
      String(
        value.status ||
          "PENDING",
      ).toUpperCase(),

    targetDelayDeltaMin:
      targetDelay,

    networkDelayDeltaMin:
      networkDelay,

    peakSectorUtilization:
      peak,

    newConflicts:
      conflicts,

    fuelMarginKg,

    fuelMarginMin,

    remainingFuelMin,

    downstreamRisk:
      String(
        downstreamRisk,
      ).toUpperCase(),

    constraintsSafe,

    routeValid,

    conflictSafe,

    restrictionSafe,

    checksAvailable:
      true,

    verifiedAtMin,

    summary:
      value.summary ||
      "Deterministic post-action verification completed.",
  };
}


function extractExecutionState(
  agentState,
  isReassessment,
) {
  if (
    isReassessment
  ) {
    return {
      executionStatus:
        "LOCKED",

      executionMode:
        "AWAITING_APPROVAL",

      verificationStatus:
        "PENDING",
    };
  }

  const events =
    asArray(
      agentState?.events,
    );

  let executionStatus =
    "LOCKED";

  let executionMode =
    "SIMULATION_FALLBACK";

  let verificationStatus =
    String(
      agentState
        ?.verification_result
        ?.status ||
        "PENDING",
    ).toUpperCase();

  for (
    const event of [
      ...events,
    ].reverse()
  ) {
    if (
      event?.event_type ===
      "EXECUTION_RESULT"
    ) {
      executionStatus =
        event?.data?.status ||
        "EXECUTED";

      executionMode =
        event?.data?.mode ||
        executionMode;
    }

    if (
      event?.event_type ===
      "VERIFICATION_RESULT"
    ) {
      verificationStatus =
        event?.data?.status ||
        verificationStatus;
    }
  }

  if (
    agentState?.status ===
      "COMPLETED" &&
    verificationStatus ===
      "PENDING"
  ) {
    verificationStatus =
      "VERIFIED";
  }

  return {
    executionStatus:
      String(
        executionStatus,
      ).toUpperCase(),

    executionMode:
      String(
        executionMode,
      ).toUpperCase(),

    verificationStatus:
      String(
        verificationStatus,
      ).toUpperCase(),
  };
}


function extractReassessmentInfo(
  agentState,
) {
  const events =
    asArray(
      agentState?.events,
    );

  const event =
    [...events]
      .reverse()
      .find(
        (item) =>
          item?.event_type ===
          "REASSESSMENT_COMPLETE",
      );

  if (!event) {
    return null;
  }

  const data =
    event.data || {};

  const rejectedCandidateId =
    data.rejected_candidate_id ||
    null;

  const rejectionReason =
    data.rejection_reason ||
    null;

  const excludedCandidateIds =
    Array.isArray(
      data.excluded_candidate_ids,
    )
      ? data.excluded_candidate_ids
      : rejectedCandidateId
        ? [rejectedCandidateId]
        : [];

  const newRecommendedCandidateId =
    data.new_recommended_candidate_id ||
    event.candidate_id ||
    null;

  return {
    rejectedCandidateId,

    rejectionReason,

    excludedCandidateIds,

    newRecommendedCandidateId,

    summary:
      data.summary ||
      event.message ||
      "AERIS completed a reassessment.",
  };
}


function stageRank(
  stage,
) {
  const stages = [
    "OBSERVE",
    "DIAGNOSE",
    "PLAN",
    "EVALUATE",
    "STRESS_TEST",
    "CRITIC",
    "RECOMMEND",
    "HUMAN_APPROVAL",
    "EXECUTE",
    "VERIFY",
    "REASSESS",
    "COMPLETE",
  ];

  return stages.indexOf(
    stage,
  );
}


function currentDisplayStage(
  agentState,
) {
  const stage =
    String(
      agentState?.stage ||
        "OBSERVE",
    ).toUpperCase();

  if (
    stage ===
    "COMPLETE"
  ) {
    return "VERIFY";
  }

  if (
    stage ===
    "REASSESS"
  ) {
    return "HUMAN_APPROVAL";
  }

  return stage;
}


function timelineItem(
  time,
  title,
  description,
) {
  return {
    time,
    title,
    description,
  };
}


function eventSimulationTime(
  events,
  eventTypes,
  fallback,
) {
  for (const event of [...asArray(events)].reverse()) {
    if (!eventTypes.has(event?.event_type)) {
      continue;
    }

    const value =
      event?.data?.simulation_time_min ??
      event?.simulation_time_min ??
      null;
    const numeric = asNumber(value);
    if (numeric !== null) {
      return numeric;
    }
  }

  return asNumber(fallback, 0);
}


function formatSimulationTime(value) {
  const numeric = Math.max(0, Math.round(asNumber(value, 0)));
  return `T+${String(numeric).padStart(2, "0")}`;
}


function buildTimeline(
  agentState,
  simulationTimeMin,
  reassessmentInfo,
) {
  const base = DEMO_TIMELINE.map((item) => ({ ...item }));
  const events = asArray(agentState?.events);

  const recommendationTime = eventSimulationTime(
    events,
    new Set(["RECOMMENDATION_READY"]),
    simulationTimeMin,
  );
  const approvalTime = eventSimulationTime(
    events,
    new Set(["APPROVAL_RESULT", "HUMAN_APPROVAL"]),
    recommendationTime,
  );
  const reassessmentTime = eventSimulationTime(
    events,
    new Set(["REASSESSMENT_COMPLETE", "CANDIDATE_REJECTED", "NO_ROBUST_INTERVENTION"]),
    simulationTimeMin,
  );
  const executionTime = eventSimulationTime(
    events,
    new Set(["EXECUTION_RESULT"]),
    simulationTimeMin,
  );

  const verification = normalizeVerification(agentState, null);
  const verifiedAt = verification.verifiedAtMin ?? eventSimulationTime(
    events,
    new Set(["VERIFICATION_RESULT"]),
    simulationTimeMin,
  );

  if (agentState?.recommendation) {
    base.push(
      timelineItem(
        formatSimulationTime(recommendationTime),
        "AERIS recommends",
        "Candidate evidence converges on the resilient network-level intervention.",
      ),
    );
  }

  if (reassessmentInfo) {
    const rejectedId = reassessmentInfo.rejectedCandidateId || "previous candidate";
    const reason = reassessmentInfo.rejectionReason || "Operator rejected the previous recommendation.";

    base.push(
      timelineItem(
        formatSimulationTime(reassessmentTime),
        "Human rejects",
        `${rejectedId} rejected: ${reason}`,
      ),
      timelineItem(
        formatSimulationTime(reassessmentTime),
        "AERIS reassesses",
        "AERIS excludes the rejected intervention and re-ranks the remaining candidates against the resilience policy.",
      ),
    );

    if (reassessmentInfo.newRecommendedCandidateId) {
      base.push(
        timelineItem(
          formatSimulationTime(reassessmentTime),
          "New recommendation",
          `AERIS now recommends ${reassessmentInfo.newRecommendedCandidateId} and requires fresh human approval.`,
        ),
      );
    } else {
      base.push(
        timelineItem(
          formatSimulationTime(reassessmentTime),
          "No robust intervention",
          "No remaining candidate met the network-resilience recommendation policy.",
        ),
      );
    }
  } else if (agentState?.approval?.decision === "APPROVED") {
    base.push(
      timelineItem(
        formatSimulationTime(approvalTime),
        "Human approves",
        "The dispatcher authorizes the selected intervention before simulated execution.",
      ),
    );
  }

  if (agentState?.approval?.decision === "APPROVED" &&
      executionTime !== recommendationTime &&
      executionTime !== simulationTimeMin) {
    base.push(
      timelineItem(
        formatSimulationTime(executionTime),
        "Simulated execution",
        "The approved intervention was applied in the deterministic simulation.",
      ),
    );
  }

  if (agentState?.verification_result?.status === "VERIFIED") {
    base.push(
      timelineItem(
        formatSimulationTime(verifiedAt),
        "Network verified",
        "Post-action constraints and network impact remain within the deterministic verification boundary.",
      ),
    );
  }

  const seen = new Set();
  return base.filter((item) => {
    const key = `${item.time}|${item.title}|${item.description}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function baseDashboard({
  worldState,
  disruptionResponse,
  networkResponse,
  flight,
  simulationTimeOverride,
}) {
  const flightCandidate =
    unwrapObject(
      flight,
      [
        "flight",
        "aircraft",
      ],
    );

  const targetId =
    flightCandidate?.id ||
    "F102";

  const targetFlight =
    normalizeFlight(
      flightCandidate ||
        findTargetFlight(
          worldState,
          targetId,
        ),
      targetId,
    );

  const simulationTimeMin =
    asNumber(
      simulationTimeOverride ??
        worldState?.time_min,
      0,
    );

  return {
    source:
      "DETERMINISTIC_ENGINE",

    mode:
      worldState?.mode ||
      "DETERMINISTIC_ENGINE",

    scenarioId:
      worldState?.scenario_id ||
      "mumbai_weather_crisis_v2",

    simulationTimeMin,

    targetFlight,

    disruption: {
      severity:
        "HIGH",

      title:
        "Active airspace disruption",

      summary:
        "AERIS is reading the current deterministic airspace state.",

      alerts:
        deriveDisruptions(
          worldState,
          disruptionResponse,
        ),
    },

    airport:
      normalizeAirport(
        worldState,
        targetFlight,
      ),

    sectors:
      asArray(
        worldState?.sectors,
      ),

    weather:
      asArray(
        worldState?.weather_cells,
      ),

    network:
      normalizeNetwork(
        worldState,
        networkResponse,
      ),

    candidates: [],

    recommendation:
      null,

    approvalStatus:
      "PENDING",

    executionStatus:
      "LOCKED",

    verificationStatus:
      "PENDING",

    executionMode:
      "SIMULATION_FALLBACK",

    verification:
      normalizeVerification(
        {},
        null,
      ),

    rejectedCandidateId:
      null,

    rejectionReason:
      null,

    excludedCandidateIds:
      [],

    isReassessment:
      false,

    agentStage:
      "OBSERVE",

    timeline:
      buildTimeline(
        null,
        simulationTimeMin,
        null,
      ),
  };
}


export function normalizeBaseline(
  data,
) {
  const airspace =
    data?.airspace ||
    {};

  const flight =
    unwrapObject(
      data?.flight,
      [
        "flight",
        "aircraft",
      ],
    ) ||
    findTargetFlight(
      airspace,
      "F102",
    );

  return baseDashboard({
    worldState:
      airspace,

    disruptionResponse:
      data?.disruptions ||
      {},

    networkResponse:
      data?.network ||
      {},

    flight,

    simulationTimeOverride:
      airspace?.time_min ??
      data?.network?.time_min ??
      0,
  });
}


export function normalizeAgentState(
  agentState,
) {
  const worldState =
    agentState?.world_state ||
    {};

  const targetId =
    agentState?.target_flight_id ||
    "F102";


  const targetFlight =
    normalizeFlight(
      findTargetFlight(
        worldState,
        targetId,
      ),
      targetId,
    );


  const reassessmentInfo =
    extractReassessmentInfo(
      agentState,
    );


  const stage =
    String(
      agentState?.stage ||
        "",
    ).toUpperCase();

  const isReassessment =
    Boolean(reassessmentInfo);

  const reassessmentPending =
    Boolean(reassessmentInfo) &&
    stage === "HUMAN_APPROVAL";


  const rawCandidates =
    asArray(
      agentState?.candidates,
    );


  const excludedSet =
    new Set(
      reassessmentInfo
        ?.excludedCandidateIds ||
        [],
    );


  const candidates =
    rawCandidates
      .map(
        normalizeCandidate,
      )
      .map(
        (candidate) => ({
          ...candidate,

          operatorRejected:
            excludedSet.has(
              candidate.id,
            ),

          rejectionReason:
            excludedSet.has(
              candidate.id,
            )
              ? reassessmentInfo
                  ?.rejectionReason ||
                candidate.rejectionReason
              : candidate.rejectionReason,
        }),
      );


  const recommendation =
    agentState?.recommendation ||
    null;


  const recommendedId =
    recommendation?.candidate_id ||
    agentState?.leading_candidate_id ||
    null;


  const terminalNoForcedFallback =
    stage === "DEGRADED" ||
    stage === "FAILED";

  const recommendedCandidate =
    candidates.find(
      (candidate) =>
        candidate.id ===
          recommendedId &&
        candidate.recommendable &&
        !candidate.operatorRejected,
    ) ||
    (!terminalNoForcedFallback &&
      candidates.find(
        (candidate) =>
          candidate.feasible &&
          candidate.recommendable &&
          !candidate.operatorRejected,
      )) ||
    null;


  const historicalApproval =
    agentState?.approval ||
    {};


  const historicalDecision =
    String(
      historicalApproval
        ?.decision ||
        "PENDING",
    ).toUpperCase();


  const currentApprovalStatus =
    reassessmentPending
      ? "PENDING"
      : historicalDecision;


  const execution =
    extractExecutionState(
      agentState,
      isReassessment,
    );


  const verification =
    isReassessment
      ? normalizeVerification(
          {},
          recommendedCandidate,
        )
      : normalizeVerification(
          agentState,
          recommendedCandidate,
        );


  const dashboard =
    baseDashboard({
      worldState,

      disruptionResponse:
        worldState?.disruptions ||
        {},

      networkResponse:
        worldState?.network_metrics ||
        {},

      flight:
        targetFlight,

      simulationTimeOverride:
        worldState?.time_min ??
        0,
    });


  dashboard.source =
    "AERIS_BACKEND_AGENT_STATE";

  dashboard.mode =
    "AERIS BACKEND";

  dashboard.scenarioId =
    agentState?.scenario_id ||
    dashboard.scenarioId;


  dashboard.candidates =
    candidates;


  dashboard.recommendation =
    recommendedCandidate
      ? {
          candidateId:
            recommendedCandidate.id,

          decisionScore:
            recommendedCandidate.decisionScore,

          confidence:
            asNumber(
              recommendation
                ?.confidence,
              0,
            ),

          summary:
            recommendation?.summary ||
            reassessmentInfo?.summary ||
            recommendedCandidate.summary,
        }
      : null;


  dashboard.approvalStatus =
    currentApprovalStatus;


  dashboard.executionStatus =
    execution.executionStatus;


  dashboard.verificationStatus =
    execution.verificationStatus;


  dashboard.executionMode =
    execution.executionMode;


  dashboard.verification =
    verification;


  dashboard.agentStage =
    currentDisplayStage(
      agentState,
    );


  dashboard.rejectedCandidateId =
    reassessmentInfo
      ?.rejectedCandidateId ||
    null;


  dashboard.rejectionReason =
    reassessmentInfo
      ?.rejectionReason ||
    null;


  dashboard.excludedCandidateIds =
    reassessmentInfo
      ?.excludedCandidateIds ||
    [];


  dashboard.isReassessment =
    isReassessment;


  if (
    !isReassessment &&
    verification.status ===
      "VERIFIED" &&
    verification.verifiedAtMin !==
      null
  ) {
    dashboard.simulationTimeMin =
      verification.verifiedAtMin;
  }


  dashboard.timeline =
    buildTimeline(
      agentState,
      dashboard.simulationTimeMin,
      isReassessment
        ? reassessmentInfo
        : null,
    );


  dashboard.rawAgentState =
    agentState;


  return dashboard;
}


export function getRecommendedCandidate(
  dashboard,
) {
  const id =
    dashboard?.recommendation
      ?.candidateId;

  return (
    dashboard?.candidates?.find(
      (candidate) =>
        candidate.id ===
          id &&
        candidate.recommendable &&
        !candidate.operatorRejected,
    ) ||
    dashboard?.candidates?.find(
      (candidate) =>
        candidate.feasible &&
        candidate.recommendable &&
        !candidate.operatorRejected,
    ) ||
    null
  );
}


export { buildTimeline };
