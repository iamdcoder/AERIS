// Scenario-only timeline checkpoints. Runtime candidate metrics always come
// from backend agent state; this file does not provide runtime dashboard data.

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