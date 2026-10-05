# AERIS Agent System

## 1. Purpose

The AERIS agent is a **controlled orchestration layer** between an operational state and a human operator.

It is not intended to replace the deterministic engine. It exists to answer questions such as:

- What is happening in the current airspace?
- Which evidence matters for this disruption?
- Which intervention families should be evaluated?
- Which candidates are operationally feasible?
- What happens to the rest of the network if we select each candidate?
- Which future scenarios can break the leading option?
- Did the critic find a better resilient alternative?
- What decision should be presented to the dispatcher?
- Has a human explicitly approved it?
- Was the result verified afterward?

---

## 2. State machine

`copilot/agent/state.py` defines the main agent stages:

```text
OBSERVE
DIAGNOSE
PLAN
EVALUATE
STRESS_TEST
CRITIC
RECOMMEND
HUMAN_APPROVAL
EXECUTE
VERIFY
REASSESS
COMPLETE
DEGRADED
FAILED
```

The transition table prevents arbitrary stage jumps.

### Normal path

```text
OBSERVE
  -> DIAGNOSE
  -> PLAN
  -> EVALUATE
  -> STRESS_TEST
  -> CRITIC
  -> RECOMMEND
  -> HUMAN_APPROVAL
  -> EXECUTE
  -> VERIFY
  -> COMPLETE
```

### Human rejection path

```text
HUMAN_APPROVAL
  -> REASSESS
  -> DIAGNOSE
```

The reassessment cycle intentionally starts again rather than applying the rejected candidate.

### Failure paths

Most active stages can transition to `DEGRADED` or `FAILED` when evidence or tool execution is not reliable enough to continue normally.

---

## 3. Observation

AERIS initially gathers:

```text
get_airspace_state
get_disruptions
get_target_flight
```

The results become the state snapshot used by downstream planning and diagnosis.

The agent stores structured evidence IDs and event records so later stages can refer back to the source of operational facts.

---

## 4. Diagnosis and investigation

The deterministic investigation layer builds questions based on observed signals such as:

- target-flight degradation;
- severe weather;
- airport degradation;
- sector pressure;
- network delay.

The hybrid Gemini path can request additional investigation-safe tools through function calling. Investigation quality is checked after execution. A run is considered complete from the Gemini investigation perspective only when the evidence is sufficient for the required operational signals.

This prevents the model from producing a persuasive text summary without collecting the necessary evidence.

---

## 5. Tool registry

The current registry exposes 13 operational capabilities:

```text
get_airspace_state
get_disruptions
get_target_flight
get_sector_state
get_airport_state
get_weather_state
get_restrictions
generate_alternatives
validate_candidate
simulate_network_impact
get_network_metrics
score_candidates
stress_test_candidate
```

Tools return structured `ToolResult` objects rather than raw exceptions whenever possible.

A tool result can carry:

```text
ok
summary
data
error_code
error_message
warnings
evidence
```

This gives the agent a consistent surface for successful and failed tool calls.

---

## 6. Gemini guardrails

Gemini function calling is wrapped by a guarded tool registry.

The investigation policy determines which tools can be called during investigation. Execution-sensitive operations are not delegated to unrestricted model choice.

The principle is:

```text
LLM proposes / investigates
          |
          v
Guarded registry
          |
          v
Deterministic tools
          |
          v
Evidence
```

The LLM is not allowed to invent a fuel margin, sector capacity, conflict result or route-feasibility result.

---

## 7. Planning

The planner converts a diagnosis into intervention families such as:

- reroute;
- altitude/speed adjustment;
- timing/hold strategy;
- alternate diversion;
- monitoring.

The planner is not itself the route solver. It selects the type of intervention to request from the engine-backed tools.

---

## 8. Evaluation

Candidates are evaluated using engine-backed evidence:

```text
hard constraints
      |
      +--> weather
      +--> fuel
      +--> performance
      +--> sector capacity
      +--> conflict / separation
      +--> restriction
      +--> airport pressure
```

An infeasible candidate should be rejected explicitly. Its rejection reasons remain part of the evidence presented to the operator.

---

## 9. Stress testing

Feasible candidates are subjected to five future perturbation profiles in the flagship scenario:

```text
F1  Weather expansion +10%
F2  Weather expansion +20%
F3  S6 capacity -15% with future bypass restriction
F4  Traffic demand +15%
F5  BOM acceptance -20%
```

Stress survival is therefore more than a generic confidence number. It records which candidate survives which deterministic future conditions.

---

## 10. Critic stage

The critic is intentionally adversarial.

Its job is not to rewrite the world model. Its job is to ask whether the current leader is fragile because of conditions such as:

- worsening weather;
- reduced sector capacity;
- increased traffic;
- newly activated restrictions;
- downstream airport degradation;
- new conflicts;
- high re-intervention probability.

For the flagship scenario, ALT-A is the locally strongest feasible candidate but fails future robustness and re-intervention checks, allowing ALT-D to become the resilient recommendation.

---

## 11. Synthesis

The synthesizer combines:

```text
ranking
+
deterministic score
+
critic result
+
selected candidate evidence
```

The final recommendation includes:

- candidate ID;
- decision status;
- confidence;
- target impact;
- network impact;
- peak sector utilization;
- affected flights;
- network resilience;
- future robustness;
- second-intervention probability;
- local-vs-global flip flag;
- critic summary;
- evidence statements;
- human-approval requirement.

The synthesizer never executes an intervention.

---

## 12. Human approval

The recommendation ends in:

```text
AWAITING_APPROVAL
```

The operator can either:

```text
APPROVE SIMULATED INTERVENTION
```

or:

```text
REJECT + REASON
```

AERIS does not treat model confidence as permission to execute.

---

## 13. Reassessment

On rejection, the system records the human reason and removes the rejected candidate from the current recommendation pool.

The rejected candidate is permanently excluded from the current decision cycle. AERIS reruns deterministic ranking and critic review. A fresh human-approval state is returned only when a recommendable candidate remains. If all remaining candidates are hard-feasible but operationally fragile under the network-resilience policy, AERIS fails closed with `NO_ROBUST_INTERVENTION_AVAILABLE` rather than forcing a route.

The frontend intentionally separates:

```text
historical rejection
```

from:

```text
current approval state
```

so an old `REJECTED`, `EXECUTED`, or `VERIFIED` status cannot leak into a new decision cycle.

---

## 14. Candidate status semantics

AERIS keeps these states distinct:

```text
hard feasible
    ↓
recommendable
    ↓
recommended
    ↓
approved
    ↓
executed
    ↓
verified
```

A candidate may be hard-feasible but not recommendable because its deterministic network/stress evidence is too fragile. Human rejection records a `rejected` state; degraded post-decision conditions use `reassessment_required` rather than silently continuing an old approval cycle.

---

## 14. Verification

After approval and execution, the engine-backed verifier checks the resulting state against the intended operational boundary.

The dashboard exposes verification status and relevant observed metrics rather than claiming success merely because execution was attempted.

The flagship successful state is:

```text
HUMAN APPROVED
EXECUTED
VERIFIED
```

---

## 15. Observability rule

AERIS exposes **observable actions and evidence**, not hidden chain-of-thought.

Good UI observability:

```text
Called get_weather_state
Weather severity HIGH
Candidate ALT-A failed future robustness
Critic challenged ALT-A
ALT-D survived 4/5 stress cases
Human approved ALT-D
Engine verified the resulting state
```

Bad UI observability:

```text
raw private model thoughts
unsupported claims presented as facts
invented aviation calculations
```
