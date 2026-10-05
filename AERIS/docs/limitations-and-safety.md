# AERIS Limitations and Safety Boundary

## 1. Simulation-only status

AERIS is a hackathon-grade deterministic simulation and decision-support prototype.

It is not an operational aviation system and should not be presented as one.

---

## 2. Synthetic data

The current scenario uses synthetic:

- aircraft;
- route graph;
- sector capacities;
- airport capacities;
- weather cells;
- restrictions;
- coordinates / geometry;
- delay dynamics;
- stress profiles.

These values are chosen to demonstrate the decision problem and are not claims about real Mumbai airspace.

---

## 3. No autonomous clearance authority

AERIS does not:

- control aircraft;
- transmit clearances;
- replace ATC;
- replace airline dispatch/OCC authority;
- represent official AAI C-ATFM/SKYFLOW decisions;
- bypass human approval.

The UI makes the human gate intentionally visible.

---

## 4. No safety-critical LLM calculations

Gemini is used for controlled investigation / tool calling and synthesis. The deterministic engine remains responsible for operational calculations.

This boundary is important because a language model can generate plausible but incorrect numerical reasoning. AERIS therefore uses tool-backed evidence for the calculations that matter to the decision.

---

## 5. Determinism

The flagship scenario is intentionally deterministic so judges can reproduce the same decision.

This is a feature for demonstration and testing, not an assertion that real aviation conditions are deterministic.

---

## 6. WebSocket status

The current backend implements `/ws/operations`. The frontend prefers WebSocket transport and falls back to `GET /operations/live` polling when WebSocket is unavailable. This is a simulated operational stream for the hackathon, not a certified production aviation feed.

---

## 7. Persistence and scaling

The copilot API currently stores active orchestrators in memory.

A production system would need a durable state store, authentication/authorization, audit logging, distributed run coordination, secrets management, observability, rate limits, and failure isolation across processes.

Those capabilities are outside the current hackathon scope.

---

## 8. Current scoring limitations

The decision scorer is deterministic and explainable, but its normalization thresholds and weights are configured for the synthetic scenario. They should not be interpreted as calibrated airline operational economics or certified resilience probabilities.

Likewise, a value such as `0.80 resilience` is a scenario metric produced by the implemented model, not a real-world probability of safe flight.

---

## 9. Responsible demo language

Preferred:

> “In our deterministic synthetic scenario, ALT-D survives 4 of 5 configured future perturbations.”

Avoid:

> “ALT-D is 80% safer in real airspace.”

Preferred:

> “The deterministic engine verifies the simulated post-action state.”

Avoid:

> “The AI guarantees the aircraft is safe.”

This distinction matters when presenting the project to technical and aviation judges.
