# AERIS Architecture

## 1. Architectural goal

AERIS separates **operational truth** from **agentic orchestration**.

The deterministic engine owns calculations that decide whether a candidate is feasible and what its simulated consequences are. The agent owns the process of deciding **what evidence to collect, which tools to invoke, how to compare evidence, when to challenge the current leader, and when to ask a human for approval**.

This separation prevents an LLM from becoming the source of aviation physics or safety-critical calculations.

---

## 2. High-level architecture

```text
+-----------------------------+
| React / Vite Command Center |
|                             |
| map / candidates / metrics  |
| decision trail / approval   |
| verification / timeline     |
+--------------+--------------+
               |
               | HTTP / JSON
               v
+--------------+--------------+
| FastAPI API Layer           |
|                             |
| airspace routes             |
| decision routes             |
| copilot routes              |
| request validation          |
+--------------+--------------+
               |
               | stable public interface
               v
+--------------+--------------+
| backend.app.engine.public   |
|                             |
| public engine facade        |
+--------------+--------------+
               |
               v
+-------------------------------------------+
| Deterministic Airspace Intelligence      |
|                                           |
| digital twin                              |
| routes                                    |
| constraints                               |
| network simulation                        |
| stress-test scenarios                     |
| decision metrics                          |
| execution / verification                  |
+-------------------------------------------+
               ^
               |
               | EngineClient
               |
+--------------+--------------+
| copilot                                    |
|                                            |
| AgentOrchestrator                          |
| investigation / diagnosis                  |
| planner                                    |
| scoring / ranking                          |
| critic                                     |
| synthesizer                                |
| approval / reassessment                    |
| execution / verification presentation      |
+------------------+-------------------------+
                   |
                   v
             Controlled tools
                   |
                   v
              Gemini API
```

---

## 3. Component responsibilities

### Frontend

The frontend is the operator-facing command center. It presents the current synthetic airspace, target flight, disruptions, candidate interventions, comparison metrics, agent stage, decision evidence, critic evidence, human gate, verification state and timeline.

The current airspace map is a custom SVG schematic. It is a visualization of the deterministic state rather than a real geospatial navigation display.

### Backend API

The FastAPI layer is intentionally thin. It transports requests and responses, validates payload shapes with Pydantic, and delegates engine work to the public facade.

### Public engine facade

`backend/app/engine/public.py` is the protected integration boundary between the engine internals and other modules.

Current public operations include:

```text
reset_engine
advance_simulation
get_airspace_state
begin_decision_context
get_decision_context
generate_alternatives
validate_candidate
simulate_candidate
stress_test_candidate
score_candidates
apply_intervention
verify_state
```

### Copilot

`copilot/` contains the agent/product layer. It is implemented as an explicit deterministic stage machine around controlled tools, structured Pydantic state, evidence records and optional Gemini investigation.

### Gemini integration

Gemini is used for controlled information gathering and investigation. Its function-calling loop is mediated by a tool registry and policy layer. It is not the source of deterministic aviation calculations.

---

## 4. Data flow for a recommendation

```text
Current engine state
       |
       v
OBSERVE
  |  get_airspace_state
  |  get_disruptions
  |  get_target_flight
       |
       v
DIAGNOSE
  |
  +--> investigation plan
  +--> targeted evidence
  +--> causal diagnosis
       |
       v
PLAN
  |
  +--> intervention families
  +--> candidate generation
       |
       v
EVALUATE
  |
  +--> hard constraints
  +--> candidate feasibility
       |
       v
STRESS TEST
  |
  +--> future perturbations
  +--> survivability
       |
       v
CRITIC
  |
  +--> challenge leader
  +--> identify future fragility
  +--> propose replacement
       |
       v
RECOMMEND
  |
  +--> recommendation
  +--> evidence
  +--> explanation
       |
       v
HUMAN APPROVAL
       |
       +---- reject ----> REASSESS
       |
       +---- approve ---> EXECUTE
                            |
                            v
                          VERIFY
```

---

## 5. Human-control boundary

The UI cannot directly turn a recommendation into an applied intervention. Approval is represented explicitly in the API and lifecycle.

The deterministic decision endpoint `/apply` requires `approved=true` and returns HTTP 403 otherwise. The copilot approval endpoint separately changes the orchestrator lifecycle and then permits execution through the lifecycle controller.

The principle is:

```text
Agent can recommend.
Agent cannot self-approve.
Agent cannot silently execute.
```

---

## 6. Failure isolation

AERIS is designed so that a failure in an outer layer should not be represented as a fake operational success.

Examples:

- Gemini unavailable → deterministic investigation fallback.
- Gemini produces insufficient evidence → deterministic investigation fallback.
- Tool returns an error → structured tool failure and agent degradation/failure handling.
- No feasible candidates → explicit no-safe-recommendation state.
- Human rejects recommendation → reassessment rather than execution.
- Verification reports a problem → reassessment/degraded state instead of falsely claiming success.

---

## 7. Current transport status

The current API exposes `/ws/operations` for the simulated operational feed. The frontend prefers WebSocket transport and falls back to `/operations/live` polling. The feed is an isolated deterministic replay used for the hackathon; it is not a production AAI/airline/ATC data connection.

This is documented explicitly rather than pretending that real-time streaming is currently implemented.
