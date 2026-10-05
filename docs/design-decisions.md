# AERIS Design Decisions

## 1. Deterministic engine as authority

### Decision

Keep operational feasibility and simulation mathematics in the deterministic engine.

### Reason

A language model can produce plausible but incorrect numerical reasoning. The system therefore makes the engine authoritative and gives the agent evidence to interpret rather than allowing the model to invent safety-critical calculations.

---

## 2. Agent around tools, not agent instead of tools

### Decision

Use a controlled tool registry for investigation and decision support.

### Reason

This makes model behavior observable and testable. Tool outputs can carry structured data, warnings and evidence IDs.

---

## 3. Human approval as a hard lifecycle gate

### Decision

No recommendation may directly become an applied intervention.

### Reason

AERIS is a decision-support system. Human authority should remain explicit, especially because the underlying model is synthetic and non-certified.

---

## 4. Frozen decision snapshots

### Decision

Validation, simulation and stress testing should be linked to a decision context.

### Reason

A candidate should be judged against the state that produced the decision, not a moving state that changes during downstream processing.

---

## 5. Critic after ranking

### Decision

Introduce an explicit critic between ranking and final synthesis.

### Reason

A high current-state score does not necessarily imply robustness under future change. The critic provides a second adversarial pass.

---

## 6. Reassessment after human rejection

### Decision

Treat rejection as a new decision cycle.

### Reason

Human disagreement should alter the decision state and trigger new reasoning, not simply mark the previous result as unsuccessful.

---

## 7. Deterministic flagship scenario

### Decision

Use synthetic, deterministic scenario inputs for the main hackathon proof.

### Reason

This makes the demonstration reproducible, testable and offline. It also avoids pretending that synthetic data is real operational aviation data.

---

## 8. Observable evidence instead of raw chain-of-thought

### Decision

Expose actions, source tools, operational evidence and decisions, but not private model reasoning.

### Reason

Judges need to see why the system acted. They do not need hidden internal reasoning presented as if it were a certified operational trace.

---

## 9. WebSocket with REST polling fallback

### Decision

Use the implemented `/ws/operations` feed as the preferred live transport, with `GET /operations/live` polling as the browser fallback.

### Reason

The WebSocket route is useful for an event-driven command center, while REST polling keeps the product recoverable when a browser, proxy or deployment does not sustain a WebSocket connection. Both transports read the same isolated deterministic operational replay.
