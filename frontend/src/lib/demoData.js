export const DEMO_DASHBOARD = {
  scenarioId: "mumbai_weather_crisis",
  simulationTimeMin: 17,
  mode: "DETERMINISTIC_MOCK",

  targetFlight: {
    id: "F102",
    callsign: "AER102",
    origin: "DEL",
    destination: "BOM",
    status: "DEGRADED",
    fuelRemainingMin: 108,
    reserveRequiredMin: 45,
    currentDelayMin: 14,
    performanceClass: "A320",
  },

  disruption: {
    severity: "HIGH",
    title: "Mumbai arrival capacity degradation",
    summary:
      "BOM arrival capacity has fallen while holding demand is increasing. Weather is expanding toward the destination corridor.",
    alerts: [
      {
        type: "AIRPORT_CAPACITY_DEGRADATION",
        severity: "HIGH",
        summary:
          "F102 is degrading because BOM arrival capacity has fallen while holding demand is increasing.",
      },
      {
        type: "SECTOR_CONGESTION",
        severity: "HIGH",
        summary:
          "Bypass sector S5 is approaching capacity as multiple flights begin shifting demand.",
      },
      {
        type: "WEATHER_EXPANSION",
        severity: "HIGH",
        summary:
          "Convective weather is expanding toward the planned destination corridor.",
      },
    ],
  },

  airport: {
    id: "BOM",
    operationalStatus: "DEGRADED",
    arrivalCapacityPer15Min: 18,
    normalArrivalCapacityPer15Min: 30,
  },

  sectors: [
    {
      id: "S4",
      status: "STRESSED",
      capacity: 12,
      projectedTraffic: 11,
      projectedUtilization: 0.92,
    },
    {
      id: "S5",
      status: "STRESSED",
      capacity: 10,
      projectedTraffic: 9,
      projectedUtilization: 0.9,
    },
  ],

  weather: {
    id: "WX-BOM-01",
    type: "CONVECTIVE",
    severity: "SEVERE",
    uncertaintyPct: 20,
    forecastExpansionPct: 20,
  },

  network: {
    activeAircraft: 40,
    aircraftInHolding: 4,
    stressedSectors: 4,
    networkDelayMin: 85.3,
  },

  candidates: [
    {
      id: "ALT-A",
      interventionType: "REROUTE",
      feasible: true,
      localScore: 0.98,
      decisionScore: 0.13,
      targetDelayMin: 0.03,
      networkDelayDeltaMin: 22.03,
      peakSectorUtilization: 1.30,
      resilience: 0.20,
      stressSurvival: 0,
      stressTotal: 5,
      fuelMarginKg: 702,
      affectedFlights: 4,
      extraDistanceKm: 0,
      rejectionReason: null,
      label: "Fastest local option",
      summary:
        "Excellent for F102 in isolation, but pushes bypass demand into an already stressed sector.",
    },

    {
      id: "ALT-B",
      interventionType: "REROUTE",
      feasible: true,
      localScore: 0.75,
      decisionScore: 0.08,
      targetDelayMin: 15.38,
      networkDelayDeltaMin: 55.38,
      peakSectorUtilization: 1.333,
      resilience: 0.10,
      stressSurvival: 0,
      stressTotal: 5,
      fuelMarginKg: 684,
      affectedFlights: 4,
      extraDistanceKm: 12,
      rejectionReason: null,
      label: "Balanced reroute",
      summary:
        "Feasible and relatively efficient, but remains sensitive to further S5 deterioration.",
    },

    {
      id: "ALT-C",
      interventionType: "ALTITUDE_SPEED",
      feasible: false,
      localScore: 0.68,
      decisionScore: null,
      targetDelayMin: 0,
      networkDelayDeltaMin: 0,
      peakSectorUtilization: 1.0,
      resilience: 0.00,
      stressSurvival: 0,
      stressTotal: 0,
      fuelMarginKg: 645,
      affectedFlights: 3,
      extraDistanceKm: 18,
      rejectionReason: "Hard constraint violation: temporary restriction intersects the candidate path.",
      label: "Restricted option",
      summary:
        "Attractive network trade-off, but the active temporary restriction makes this intervention invalid.",
    },

    {
      id: "ALT-D",
      interventionType: "REROUTE",
      feasible: true,
      localScore: 0.82,
      decisionScore: 0.36,
      targetDelayMin: 4.49,
      networkDelayDeltaMin: 12.49,
      peakSectorUtilization: 1.00,
      resilience: 0.80,
      stressSurvival: 4,
      stressTotal: 5,
      fuelMarginKg: 610,
      affectedFlights: 3,
      extraDistanceKm: 42,
      rejectionReason: null,
      label: "Resilient network route",
      summary:
        "Slightly worse locally, but produces the strongest network outcome and survives 4/5 tested future scenarios.",
    },

    {
      id: "ALT-E",
      interventionType: "ALTERNATE_DIVERSION",
      feasible: false,
      localScore: 0.75,
      decisionScore: null,
      targetDelayMin: 10,
      networkDelayDeltaMin: -18,
      peakSectorUtilization: 0.78,
      resilience: 0.25,
      stressSurvival: 5,
      stressTotal: 5,
      fuelMarginKg: 388,
      affectedFlights: 1,
      extraDistanceKm: 71,
      rejectionReason: "Hard constraint violation: fuel margin below minimum.",
      label: "Maximum avoidance",
      summary:
        "Excellent network isolation, but insufficient fuel safety margin makes the option operationally invalid.",
    },
  ],

  simulations: {
    "ALT-B": {
      targetDelayDeltaMin: -10,
      affectedFlights: 4,
      networkDelayDeltaMin: 2,
      peakSectorUtilization: 0.94,
      newConflicts: 0,
      downstreamRisk: "MEDIUM",
    },

    "ALT-C": {
      targetDelayDeltaMin: -9,
      affectedFlights: 3,
      networkDelayDeltaMin: -3,
      peakSectorUtilization: 0.86,
      newConflicts: 0,
      downstreamRisk: "LOW",
    },

    "ALT-D": {
      targetDelayDeltaMin: -6,
      affectedFlights: 1,
      networkDelayDeltaMin: -14,
      peakSectorUtilization: 0.82,
      newConflicts: 0,
      downstreamRisk: "VERY_LOW",
    },
  },

  stressTests: {
    "ALT-B": {
      passed: 0,
      total: 5,
      criticalFailure: "High network delay and sector overload make the candidate non-resilient.",
      scenarios: [
        "BASELINE",
        "WEATHER +10%",
        "WEATHER +20%",
        "TRAFFIC +10%",
        "CAPACITY -20%",
      ],
    },

    "ALT-C": {
      passed: 0,
      total: 5,
      criticalFailure:
        "Candidate is rejected by the active temporary restriction before stress scoring.",
      scenarios: [
        "BASELINE",
        "WEATHER +10%",
        "WEATHER +20%",
        "TRAFFIC +10%",
        "CAPACITY -20%",
      ],
    },

    "ALT-D": {
      passed: 4,
      total: 5,
      criticalFailure: "Traffic demand +15% pushes one modeled sector above the threshold.",
      scenarios: [
        "WEATHER +10% PASS",
        "WEATHER +20% PASS",
        "CAPACITY -15% + restriction PASS",
        "TRAFFIC +15% FAIL",
        "BOM -20% PASS",
      ],
    },
  },

  recommendation: {
    candidateId: "ALT-D",
    decisionScore: 0.92,
    confidence: 0.91,
    targetBenefit: 0.82,
    networkResilience: 0.91,
    networkImpactScore: 0.94,
    fuelSafetyMargin: 0.87,
    futureRobustness: 0.80,
    requiresHumanApproval: true,
    summary:
      "ALT-D is recommended because its lower network ripple and stronger resilience outweigh its local delay cost.",
  },

  verification: {
    targetDelayDeltaMin: -6,
    networkDelayDeltaMin: -14,
    peakSectorUtilization: 0.82,
    newConflicts: 0,
    fuelMarginKg: 610,
    downstreamRisk: "VERY_LOW",
  },
};

export const DEMO_TIMELINE = [
  {
    time: "T+00",
    title: "Baseline",
    description: "Network operating normally.",
  },
  {
    time: "T+05",
    title: "Weather expands",
    description: "Convective weather begins moving toward the BOM corridor.",
  },
  {
    time: "T+08",
    title: "Capacity degradation",
    description: "Mumbai arrival capacity drops from normal levels.",
  },
  {
    time: "T+12",
    title: "Holding builds",
    description: "Arrival demand begins creating measurable network pressure.",
  },
  {
    time: "T+15",
    title: "Ripple emerges",
    description: "Bypass sector S5 becomes stressed.",
  },
  {
    time: "T+17",
    title: "AERIS investigates",
    description: "F102 degradation triggers the agentic investigation.",
  },
];