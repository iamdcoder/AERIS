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
    activeAircraft: 48,
    aircraftInHolding: 4,
    stressedSectors: 2,
    networkDelayMin: 31,
  },

  candidates: [
    {
      id: "ALT-A",
      interventionType: "REROUTE",
      feasible: false,
      localScore: 0.98,
      decisionScore: null,
      targetDelayMin: 2,
      networkDelayDeltaMin: 9,
      peakSectorUtilization: 1.08,
      resilience: 0.41,
      stressSurvival: 2,
      stressTotal: 5,
      fuelMarginKg: 702,
      affectedFlights: 7,
      extraDistanceKm: 0,
      rejectionReason: "Hard constraint violation: S5 projected overload.",
      label: "Fastest local option",
      summary:
        "Excellent for F102 in isolation, but pushes bypass demand into an already stressed sector.",
    },

    {
      id: "ALT-B",
      interventionType: "REROUTE",
      feasible: true,
      localScore: 0.96,
      decisionScore: 0.84,
      targetDelayMin: 4,
      networkDelayDeltaMin: 2,
      peakSectorUtilization: 0.94,
      resilience: 0.66,
      stressSurvival: 3,
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
      feasible: true,
      localScore: 0.88,
      decisionScore: 0.87,
      targetDelayMin: 5,
      networkDelayDeltaMin: -3,
      peakSectorUtilization: 0.86,
      resilience: 0.81,
      stressSurvival: 4,
      stressTotal: 5,
      fuelMarginKg: 645,
      affectedFlights: 3,
      extraDistanceKm: 18,
      rejectionReason: null,
      label: "Network-aware option",
      summary:
        "Reduces ripple effects substantially, but remains exposed to downstream airport degradation.",
    },

    {
      id: "ALT-D",
      interventionType: "REROUTE",
      feasible: true,
      localScore: 0.82,
      decisionScore: 0.92,
      targetDelayMin: 8,
      networkDelayDeltaMin: -14,
      peakSectorUtilization: 0.82,
      resilience: 0.91,
      stressSurvival: 5,
      stressTotal: 5,
      fuelMarginKg: 610,
      affectedFlights: 1,
      extraDistanceKm: 42,
      rejectionReason: null,
      label: "Resilient network route",
      summary:
        "Slightly worse locally, but produces the strongest network outcome and survives every tested future scenario.",
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
      resilience: 0.94,
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
      passed: 3,
      total: 5,
      criticalFailure: "Sector S5 overloads after 20% weather expansion.",
      scenarios: [
        "BASELINE",
        "WEATHER +10%",
        "WEATHER +20%",
        "TRAFFIC +10%",
        "CAPACITY -20%",
      ],
    },

    "ALT-C": {
      passed: 4,
      total: 5,
      criticalFailure:
        "Downstream airport degradation causes a second intervention requirement.",
      scenarios: [
        "BASELINE",
        "WEATHER +10%",
        "WEATHER +20%",
        "TRAFFIC +10%",
        "CAPACITY -20%",
      ],
    },

    "ALT-D": {
      passed: 5,
      total: 5,
      criticalFailure: null,
      scenarios: [
        "WEATHER +10% PASS",
        "WEATHER +20% PASS",
        "CAPACITY -10% PASS",
        "CAPACITY -20% PASS",
        "TRAFFIC +10% PASS",
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
    futureRobustness: 1.0,
    requiresHumanApproval: true,
    summary:
      "ALT-D is recommended because its network resilience and future robustness outweigh its local delay cost.",
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