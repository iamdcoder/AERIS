import { DEMO_TIMELINE } from "./demoData";


function asNumber(
  value,
  fallback = null,
) {
  const parsed = Number(
    value,
  );

  return Number.isFinite(
    parsed,
  )
    ? parsed
    : fallback;
}


function asPercentRatio(
  value,
) {
  const number =
    asNumber(value);

  if (number === null) {
    return 0;
  }

  if (number > 2) {
    return number / 100;
  }

  return number;
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

  return (
    worldState?.aircraft?.find(
      (flight) =>
        flight.id === flightId,
    ) || null
  );
}


function normalizeFlight(
  flight,
) {
  if (!flight) {
    return {
      id: "F102",
      callsign: "AER102",
      origin: "DEL",
      destination: "BOM",
      status: "UNKNOWN",
      fuelRemainingMin: 0,
      reserveRequiredMin: 0,
      currentDelayMin: 0,
      performanceClass: "UNKNOWN",
    };
  }

  return {
    id:
      flight.id || "F102",

    callsign:
      flight.callsign ||
      flight.id ||
      "UNKNOWN",

    origin:
      flight.origin ||
      flight.route?.[0] ||
      "N/A",

    destination:
      flight.destination ||
      flight.route?.[
        flight.route.length - 1
      ] ||
      "N/A",

    status:
      flight.status ||
      "UNKNOWN",

    fuelRemainingMin:
      asNumber(
        flight.fuel_remaining_min,
        0,
      ),

    reserveRequiredMin:
      asNumber(
        flight.reserve_required_min,
        0,
      ),

    currentDelayMin:
      asNumber(
        flight.delay_min,
        flight.current_delay_min ||
          0,
      ),

    performanceClass:
      flight.performance_class ||
      "UNKNOWN",
  };
}


function normalizeCandidate(
  candidate,
) {
  const stress =
    candidate.stress_survival;

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
    typeof stress ===
    "string"
  ) {
    const match =
      stress.match(
        /(\d+)\s*\/\s*(\d+)/,
      );

    if (match) {
      stressPassed =
        Number(match[1]);

      stressTotal =
        Number(match[2]);
    }
  }

  const resilience =
    asNumber(
      candidate.resilience_score,
      asNumber(
        candidate.resilience_metrics
          ?.future_robustness,
        0,
      ),
    );

  const peak =
    asPercentRatio(
      candidate.max_sector_utilization_pct ??
        candidate.peak_sector_utilization,
    );

  const strategy =
    candidate.strategy ||
    candidate.intervention_type ||
    "INTERVENTION";

  const readableStrategy =
    String(strategy)
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
    candidate.rejection_reasons ||
    [];

  const explanation =
    candidate.score_explanation ||
    candidate.explanation ||
    (
      rejectionReasons.length
        ? rejectionReasons.join(
            "; ",
          )
        : `${readableStrategy} candidate evaluated by the deterministic engine.`
    );

  return {
    id:
      candidate.candidate_id ||
      candidate.id ||
      "UNKNOWN",

    interventionType:
      readableStrategy,

    feasible:
      candidate.feasible === true,

    localScore:
      candidate.local_score ??
      null,

    decisionScore:
      candidate.decision_score ??
      null,

    targetDelayMin:
      asNumber(
        candidate.target_delay_min,
        0,
      ),

    networkDelayDeltaMin:
      asNumber(
        candidate.network_delay_delta_min,
        0,
      ),

    peakSectorUtilization:
      peak,

    resilience,

    stressSurvival:
      stressPassed,

    stressTotal,

    affectedFlights:
      asNumber(
        candidate.affected_flights,
        0,
      ),

    fuelMarginKg:
      candidate.fuel_margin_kg ??
      null,

    fuelMarginMin:
      candidate.fuel_reserve_margin_min ??
      null,

    extraDistanceKm:
      asNumber(
        candidate.added_distance_km,
        0,
      ),

    label:
      candidate.label ||
      readableStrategy,

    summary:
      explanation,

    rejectionReason:
      rejectionReasons.length
        ? rejectionReasons.join(
            "; ",
          )
        : candidate.route_validation_error ||
          null,

    raw: candidate,
  };
}


function deriveDisruptions(
  worldState,
  response,
) {
  const existing =
    worldState?.alerts ||
    (
      worldState?.disruptions?.disruptions
    ) ||
    response?.weather_cells ||
    [];

  const alerts = [];

  if (
    Array.isArray(
      existing,
    )
  ) {
    existing.forEach(
      (item) => {
        if (
          item &&
          item.type
        ) {
          alerts.push(
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
      },
    );
  }

  if (!alerts.length) {
    for (
      const cell
      of worldState?.weather_cells ||
      []
    ) {
      const intensity =
        String(
          cell.intensity ||
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
        alerts.push(
          {
            type:
              "WEATHER_EXPANSION",
            severity:
              intensity,
            summary:
              `Weather cell ${cell.id || "UNKNOWN"} is ${intensity.toLowerCase()} in the current simulation.`,
          },
        );
      }
    }
  }

  return alerts;
}


function normalizeNetwork(
  worldState,
  networkResponse,
) {
  const aircraft =
    worldState?.aircraft ||
    [];

  const sectors =
    worldState?.sectors ||
    [];

  const totalDelayFromState =
    aircraft.reduce(
      (
        total,
        flight,
      ) =>
        total +
        asNumber(
          flight.delay_min,
          0,
        ),
      0,
    );

  const holding =
    aircraft.filter(
      (flight) =>
        String(
          flight.status ||
            "",
        ).toUpperCase()
        === "HOLDING",
    ).length;

  const stressed =
    sectors.filter(
      (sector) => {
        const status =
          String(
            sector.status ||
              "",
          ).toUpperCase();

        const utilization =
          asPercentRatio(
            sector.utilization_pct ??
              sector.projected_utilization,
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
          utilization >= 0.85
        );
      },
    ).length;

  return {
    activeAircraft:
      networkResponse?.total_flights ??
      aircraft.length,

    aircraftInHolding:
      networkResponse?.holding_flights ??
      holding,

    stressedSectors:
      stressed,

    networkDelayMin:
      networkResponse?.total_delay_min ??
      totalDelayFromState,
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
    worldState?.airports ||
    [];

  const airport =
    airports.find(
      (item) =>
        item.id === destination,
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
      airport.id,

    operationalStatus:
      airport.operational_status ||
      "NORMAL",

    arrivalCapacityPer15Min:
      airport.arrival_capacity ??
      null,

    normalArrivalCapacityPer15Min:
      airport.normal_arrival_capacity ??
      null,
  };
}


function normalizeVerification(
  agentState,
) {
  const value =
    agentState?.verification_result;

  if (!value) {
    return {
      targetDelayDeltaMin: 0,
      networkDelayDeltaMin: 0,
      peakSectorUtilization: 0,
      newConflicts: 0,
      fuelMarginKg: 0,
      downstreamRisk: "UNKNOWN",
    };
  }

  return {
    targetDelayDeltaMin:
      asNumber(
        value.after_metrics
          ?.target_delay_delta_min ??
          value.target_delay_delta_min,
        0,
      ),

    networkDelayDeltaMin:
      asNumber(
        value.after_metrics
          ?.network_delay_delta_min ??
          value.network_delay_delta_min,
        0,
      ),

    peakSectorUtilization:
      asPercentRatio(
        value.after_metrics
          ?.max_sector_utilization_pct ??
          value.after_metrics
            ?.peak_sector_utilization ??
          value.peak_sector_utilization,
      ),

    newConflicts:
      asNumber(
        value.after_metrics
          ?.new_conflicts ??
          value.new_conflicts,
        0,
      ),

    fuelMarginKg:
      asNumber(
        value.after_metrics
          ?.fuel_margin_kg ??
          value.fuel_margin_kg,
        0,
      ),

    downstreamRisk:
      value.after_metrics
        ?.downstream_risk ||
      value.downstream_risk ||
      "UNKNOWN",
  };
}


function extractExecutionState(
  agentState,
) {
  const events =
    agentState?.events ||
    [];

  let executionStatus =
    "LOCKED";

  let executionMode =
    "SIMULATION_FALLBACK";

  let verificationStatus =
    agentState
      ?.verification_result
      ?.status ||
    "PENDING";

  for (
    const event
    of [...events].reverse()
  ) {
    if (
      event.event_type ===
      "EXECUTION_RESULT"
    ) {
      executionStatus =
        event.data?.status ||
        "EXECUTED";

      executionMode =
        event.data?.mode ||
        executionMode;
    }

    if (
      event.event_type ===
      "VERIFICATION_RESULT"
    ) {
      verificationStatus =
        event.data?.status ||
        verificationStatus;
    }
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


function currentDisplayStage(
  agentState,
) {
  const stage =
    String(
      agentState?.stage ||
        "OBSERVE",
    ).toUpperCase();

  if (
    stage === "COMPLETE"
  ) {
    return "VERIFY";
  }

  if (
    stage === "REASSESS"
  ) {
    return "HUMAN_APPROVAL";
  }

  return stage;
}


function baseDashboard({
  worldState,
  disruptionResponse,
  networkResponse,
  flight,
}) {
  const targetFlight =
    normalizeFlight(
      flight ||
        findTargetFlight(
          worldState,
          "F102",
        ),
    );

  return {
    source:
      "DETERMINISTIC_ENGINE",

    mode:
      worldState?.mode ||
      "DETERMINISTIC_ENGINE",

    scenarioId:
      worldState?.scenario_id ||
      "mumbai_weather_crisis",

    simulationTimeMin:
      worldState?.time_min ??
      0,

    targetFlight,

    disruption: {
      severity: "HIGH",

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
      worldState?.sectors ||
      [],

    weather:
      worldState?.weather_cells ||
      [],

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
      ),

    agentStage:
      "OBSERVE",

    timeline:
      DEMO_TIMELINE,
  };
}


export function normalizeBaseline(
  data,
) {
  return baseDashboard(
    {
      worldState:
        data?.airspace ||
        {},

      disruptionResponse:
        data?.disruptions ||
        {},

      networkResponse:
        data?.network ||
        {},

      flight:
        data?.flight ||
        null,
    },
  );
}


export function normalizeAgentState(
  agentState,
) {
  const worldState =
    agentState?.world_state ||
    {};

  const targetFlight =
    normalizeFlight(
      findTargetFlight(
        worldState,
        agentState?.target_flight_id ||
          "F102",
      ),
    );

  const candidates = (
    agentState?.candidates ||
    []
  ).map(
    normalizeCandidate,
  );

  const recommendation =
    agentState?.recommendation ||
    null;

  const recommendedId =
    recommendation?.candidate_id ||
    agentState?.leading_candidate_id ||
    null;

  const recommendedCandidate =
    candidates.find(
      (candidate) =>
        candidate.id ===
        recommendedId,
    ) ||
    null;

  const execution =
    extractExecutionState(
      agentState,
    );

  const dashboard =
    baseDashboard(
      {
        worldState,
        disruptionResponse:
          worldState?.disruptions ||
          {},
        networkResponse:
          {},
        flight: targetFlight,
      },
    );

  dashboard.source =
    "AERIS_BACKEND_AGENT_STATE";

  dashboard.mode =
    "AERIS BACKEND";

  dashboard.candidates =
    candidates;

  dashboard.recommendation =
    recommendedCandidate
      ? {
          candidateId:
            recommendedCandidate.id,

          decisionScore:
            asNumber(
              recommendedCandidate.decisionScore,
              0,
            ),

          confidence:
            asNumber(
              recommendation?.confidence,
              0,
            ),

          summary:
            recommendation?.summary ||
            recommendedCandidate.summary,
        }
      : null;

  dashboard.approvalStatus =
    String(
      agentState?.approval
        ?.decision ||
        "PENDING",
    ).toUpperCase();

  dashboard.executionStatus =
    execution.executionStatus;

  dashboard.verificationStatus =
    execution.verificationStatus;

  dashboard.executionMode =
    execution.executionMode;

  dashboard.verification =
    normalizeVerification(
      agentState,
    );

  dashboard.agentStage =
    currentDisplayStage(
      agentState,
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
        candidate.id === id,
    ) || null
  );
}