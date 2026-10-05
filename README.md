# AERIS

## Agentic Airspace Resilience Intelligence System

AERIS is a **human-supervised agentic decision-support system for aviation operations**. It evaluates intervention choices for a disrupted flight not only by what they do to the target aircraft, but also by the network-wide consequences and by how the candidates behave under deterministic future stress scenarios.

AERIS is a **decision-support prototype, not a chatbot and not an autonomous air-traffic control system**. The deterministic airspace engine is authoritative for operational feasibility, physical constraints, simulation and verification. The agent coordinates investigation, invokes controlled tools, compares evidence, uses an adversarial critic to challenge the leading option, synthesizes a recommendation, and stops for explicit human approval before execution.

Live Deployment: https://aeris-frontend-v9ji.onrender.com/

Live Demo: https://youtu.be/pxSoBqND1tE

> **Core idea:** the best route for one aircraft is not necessarily the best intervention for the network.

---

## What the system demonstrates

The flagship decision lifecycle is:

```text
AIRSPACE STATE
      ↓
   OBSERVE
      ↓
  DIAGNOSE
      ↓
    PLAN
      ↓
  EVALUATE
      ↓
 STRESS TEST
      ↓
   CRITIC
      ↓
 RECOMMEND
      ↓
HUMAN APPROVAL
   ↙       ↘
REJECT    APPROVE
  ↓          ↓
REASSESS   EXECUTE
             ↓
          VERIFY
             ↓
          COMPLETE
```

The repository is intentionally split into two logical layers:

**Deterministic Airspace Intelligence**
- digital-twin state and simulation;
- route and intervention generation;
- hard constraint validation;
- multi-flight network impact simulation;
- future stress testing;
- decision metrics;
- execution and post-action verification.

**Agent + Product**
- investigation and diagnosis;
- controlled tool orchestration;
- planning and candidate ranking;
- adversarial challenge;
- recommendation synthesis;
- human approval/rejection lifecycle;
- evidence presentation and command-center UI;
- operational replay and reassessment.

---

## Flagship scenario: Mumbai Monsoon Multi-Constraint Network Crisis

AERIS ships a reproducible synthetic scenario designed to make the local-vs-network trade-off visible.

| Property | Value |
|---|---|
| Scenario | `mumbai_weather_crisis_v2` |
| Target flight | F102 / AI102 |
| Airport focus | BOM |
| Simulated duration | 35 minutes |
| Aircraft | 40 |
| Decision snapshot | T+19 |

The disruption combines interacting pressures including convective weather near BOM, reduced airport acceptance, holding, sector-capacity pressure, target-flight degradation, and a temporary airspace restriction.

At T+19 the deterministic engine produces five candidates:

| Candidate | Status | Key result |
|---|---|---|
| ALT-A | Feasible | Very strong immediate target-flight result, but poor network/future resilience |
| ALT-B | Feasible | Higher target-flight delay and weak network outcome |
| ALT-C | Rejected | Violates the active restriction condition |
| ALT-D | Feasible | Best network-resilience trade-off |
| ALT-E | Rejected | Cannot preserve the configured fuel reserve |

### Why ALT-D wins

The flagship comparison is deliberately non-local:

| Metric | ALT-A | ALT-D |
|---|---:|---:|
| Target delay | +0.03 min | +4.49 min |
| Network delay delta | +22.03 min | +12.49 min |
| Peak sector utilization | 130% | 100% |
| Stress survival | 0/5 | 4/5 |
| Re-intervention probability | 100% | 20% |
| Decision score | 0.92 local* | 0.36 |

\* The `0.92` figure is the local/preliminary score shown by the judge/demo materials; the final deterministic ranking uses the network-aware decision score. The point of the scenario is the **local leader → network-resilient recommendation reversal**, not the absolute magnitude of either score.

The actual agent proof records ALT-A as the preliminary/local leader, challenges it during the critic stage, and produces ALT-D as the final recommendation.

---

## Decision pipeline in more detail

### 1. Observe

The agent starts from the current deterministic airspace state and gathers operational evidence such as:
- overall airspace state;
- active disruptions;
- target-flight status.

### 2. Diagnose

AERIS identifies the signals that matter to the decision, such as weather severity, airport degradation, sector pressure, target-flight degradation and network delay.

### 3. Plan

The planner selects intervention families and requests candidate generation from engine-backed tools. The agent does not solve routes or calculate safety-critical quantities by itself.

### 4. Evaluate

Every candidate is checked against hard operational constraints including:
- weather;
- fuel reserve;
- aircraft performance;
- sector capacity;
- conflict/separation;
- temporary restrictions;
- airport pressure.

Only feasible candidates continue to simulation and stress testing.

### 5. Stress test

The flagship evaluates candidates against five deterministic future perturbations:

```text
F1  Weather expansion +10%
F2  Weather expansion +20%
F3  S6 capacity -15% with future bypass restriction
F4  Traffic demand +15%
F5  BOM acceptance -20%
```

For the flagship scenario:
- ALT-A: 0/5;
- ALT-B: 0/5;
- ALT-D: 4/5.

The 4/5 result is a **scenario metric**, not a real-world safety probability.

### 6. Critic

The critic is intentionally adversarial. It challenges the preliminary leader when evidence indicates fragility from factors such as future weather, sector capacity, traffic, downstream effects, conflict risk or likely re-intervention.

### 7. Recommend

The synthesizer combines deterministic ranking, simulation/stress evidence and critic findings into an operator-facing recommendation.

### 8. Human approval

The system stops at the approval boundary:

```text
AWAITING_APPROVAL
```

The recommendation cannot be applied merely because the model is confident.

### 9. Execute and verify

After explicit approval, the intervention is applied through the deterministic engine and the resulting state is verified.

The successful flagship path is:

```text
HUMAN APPROVED
      ↓
EXECUTED
      ↓
VERIFIED
```

### 10. Reject and reassess

A rejection is a real lifecycle event, not a UI label change.

The rejected candidate is removed from the current recommendation cycle. AERIS reassesses the remaining candidates. In the flagship rejection proof, rejecting ALT-D leaves no candidate that satisfies the recommendation policy, so the system **fails closed**:

```text
REJECT ALT-D
     ↓
REASSESS
     ↓
NO ROBUST INTERVENTION AVAILABLE
     ↓
DEGRADED
```

It does not force a fragile fallback back into the approval queue.

---

## Agentic architecture

```text
                         +------------------------+
                         |     React + Vite       |
                         |   AERIS Command Center |
                         +-----------+------------+
                                     |
                            HTTP / REST + WebSocket
                                     |
                                     v
                         +-----------+------------+
                         |        FastAPI         |
                         | API + operational feed |
                         +-----------+------------+
                                     |
                              public engine API
                                     |
                                     v
                  +------------------+------------------+
                  |     Deterministic Airspace Engine  |
                  |                                    |
                  | digital twin                       |
                  | route generation                   |
                  | hard constraints                   |
                  | network simulation                 |
                  | stress testing                     |
                  | scoring / metrics                  |
                  | execution / verification           |
                  +------------------+------------------+
                                     ^
                                     |
                                EngineClient
                                     |
                         +-----------+------------+
                         |     AERIS Copilot      |
                         |                        |
                         | orchestrator            |
                         | investigation           |
                         | diagnostics             |
                         | planner / ranker         |
                         | critic                  |
                         | synthesizer             |
                         | approval / reassessment |
                         | verification            |
                         +-----------+------------+
                                     |
                               guarded tools
                                     |
                                     v
                                Gemini API
```

### Authority boundary

The LLM is **not** the source of truth for safety-critical calculations.

The deterministic engine supplies the authoritative values for things such as:
- fuel and reserve checks;
- sector capacity;
- conflict/separation;
- restrictions;
- route feasibility;
- network simulation;
- resilience metrics;
- execution verification.

The agent is responsible for orchestration, evidence gathering, comparison, challenge and synthesis.

This separation is central to the project's design: **LLM for controlled investigation; deterministic engine for operational truth.**

---

## Live operational replay

The repository also includes a deterministic operational-event replay layer.

It simulates changing operational inputs rather than claiming a connection to production AAI, airline, ATC or meteorological feeds.

### Event flow

```text
scenario / future adapter
        ↓
OperationalEvent
        ↓
OperationalStateStore
        ↓
current operational snapshot
    ↙             ↘
 REST           WebSocket
  ↓                ↓
          AERIS command center
```

The current transport is:

```text
GET /operations/live
GET /operations/events?limit=20

POST /operations/replay/reset
POST /operations/replay/start
POST /operations/replay/stop
POST /operations/replay/step

WS /ws/operations
```

The browser prefers WebSocket and falls back to REST polling when WebSocket transport is unavailable.

The replay can progress through T+35. The flagship decision snapshot remains T+19. When the simulated feed advances beyond the decision point, the dashboard can reassess current conditions using a fresh authoritative engine snapshot.

---

## Human-in-the-loop workflow

AERIS deliberately separates **recommendation** from **execution**.

### Approval

The command center exposes an explicit human gate. The operator can approve the simulated intervention or reject it with a reason.

### Rejection

The current implementation records the rejection, removes the candidate from the active decision cycle, and reassesses. The system never interprets rejection as permission to try the same intervention again.

### Single-process runtime note

Active copilot runs are stored in memory. Run state is therefore local to the FastAPI process and is lost when the backend restarts. The demo should use a **single Uvicorn process without multiple workers** so the in-memory human-approval lifecycle remains coherent.

---

## Repository structure

```text
AERIS/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── airspace.py
│   │   │   │   ├── copilot.py
│   │   │   │   ├── decisions.py
│   │   │   │   ├── health.py
│   │   │   │   └── operations.py
│   │   │   ├── schemas/
│   │   │   └── app.py
│   │   ├── engine/
│   │   │   ├── digital_twin/
│   │   │   ├── constraints/
│   │   │   ├── routes/
│   │   │   ├── simulation/
│   │   │   ├── stress_test/
│   │   │   ├── metrics/
│   │   │   └── public.py
│   │   ├── models/
│   │   └── operations/
│   ├── data/
│   └── tests/
├── copilot/
│   ├── agent/
│   ├── engine/
│   ├── llm/
│   ├── mock_engine/
│   ├── tools/
│   └── tests/
├── frontend/
│   └── src/
├── contracts/
├── scenarios/
├── scripts/
├── docs/
├── requirements.txt
├── pyproject.toml
├── .env.example
├── OWNERSHIP.md
└── CONTRIBUTING.md
```

---

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python |
| API | FastAPI |
| Data models / validation | Pydantic |
| Network graph | NetworkX |
| Geometry | Shapely |
| Agent LLM | Gemini via `google-genai` |
| Agent orchestration | Custom AERIS state machine |
| Frontend | React 19 + Vite 8 |
| Visualization | Custom SVG airspace visualization + Recharts dependency |
| Testing | pytest + Node test runner |
| Contracts | JSON Schema + Markdown |

The current frontend package does **not** use Deck.gl; the airspace visualization is implemented with custom SVG.

---

## Local setup

### Prerequisites

- Python 3.10+
- Node.js / npm
- A Gemini API key only when using the hybrid recommendation path

### 1. Clone

```bash
git clone https://github.com/iamdcoder/AERIS.git
cd AERIS
```

### 2. Python environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment

Create a local `.env` from `.env.example`.

For Gemini-backed investigation:

```text
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

The application can run its deterministic flagship path without Gemini.

### 4. Start FastAPI

From the repository root:

```bash
python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000
```

Keep one backend process for the live demo.

Useful endpoints:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

### 5. Start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite development server proxies `/api` requests and `/ws` connections to `127.0.0.1:8000`.

---

## Running the proofs

### Deterministic engine proof

```bash
python scripts/run_flagship.py
```

This is offline-safe and does not require Gemini or network access. It exercises the deterministic lifecycle through:

```text
DISRUPTION
→ CANDIDATES
→ VALIDATION
→ SIMULATION
→ STRESS TEST
→ DECISION
→ HUMAN APPROVAL
→ EXECUTE
→ VERIFY
```

### Agentic proof

```bash
python scripts/run_agent_flagship.py
```

This exercises the FastAPI copilot path and verifies:
- local-vs-network reversal;
- critic challenge;
- human approval;
- execution and verification;
- rejection/reassessment;
- fail-closed behavior when no robust option remains.

### Live replay proof

```bash
python scripts/run_live_replay.py
```

Optional stop point:

```bash
python scripts/run_live_replay.py --stop-at 35
```

### Submission preflight

```bash
python scripts/preflight_submission.py
```

The preflight checks compilation, Python tests, both flagship runners, live replay, API health/WebSocket connectivity, frontend adapter tests, documentation consistency and submission hygiene.

---

## API overview

### Read endpoints

```text
GET  /health
GET  /airspace
GET  /flights/{flight_id}
GET  /disruptions
GET  /network/metrics
GET  /operations/live
GET  /operations/events?limit=20
```

### Deterministic decision endpoints

```text
POST /alternatives
POST /validate
POST /simulate
POST /stress-test
POST /decision-score
POST /apply
POST /verify
```

### Copilot lifecycle

```text
POST /copilot/investigate
POST /copilot/recommend
POST /copilot/approve
POST /copilot/reject
POST /copilot/reset
```

### Operational replay controls

```text
POST /operations/replay/reset
POST /operations/replay/start
POST /operations/replay/stop
POST /operations/replay/step
WS   /ws/operations
```

Full payload details are documented in [`docs/api-reference.md`](docs/api-reference.md) and [`contracts/api-contract.md`](contracts/api-contract.md).

---

## Deterministic vs hybrid modes

AERIS supports two practical operating modes:

### Deterministic mode

Used by `/copilot/investigate` and the offline flagship proofs.

```text
deterministic investigation
        ↓
deterministic engine
        ↓
recommendation
```

### Hybrid mode

Used by `/copilot/recommend`.

```text
Gemini investigation
        ↓
guarded tool registry
        ↓
structured evidence
        ↓
deterministic engine-backed evaluation
        ↓
critic / synthesis
        ↓
human approval
```

When Gemini is unavailable or the investigation does not produce sufficient evidence, the hybrid path falls back to deterministic investigation instead of fabricating operational facts.

---

## Safety and limitations

AERIS is a **hackathon-grade synthetic simulation and decision-support prototype**.

The current repository does not:
- control real aircraft;
- issue ATC clearances;
- replace airline dispatch/OCC authority or ATC;
- represent official AAI operational decisions;
- provide certified aviation safety calculations;
- guarantee real-world route legality or safety;
- use privileged live aviation data.

Aircraft, route topology, coordinates, capacities, weather, restrictions, fuel and delay behavior are synthetic values chosen for reproducible demonstration.

Important distinction:

> “ALT-D survived 4 of 5 configured future perturbations in our synthetic scenario.”

is valid demo language.

> “ALT-D is 80% safer in real airspace.”

is not.

Production deployment would require, among other things, authenticated access, authorization, durable state, audit logging, distributed coordination, secure secret management, observability, stronger failure isolation, and aviation-domain certification/validation appropriate to the use case.

---

## Testing status

The repository's current build-status documentation reports:

```text
Backend suite        286 passed
Copilot suite        123 passed, 5 skipped
Combined             409 passed, 5 skipped
Agent flagship       SUCCESS
Live replay          SUCCESS through T+35
FastAPI health       HTTP 200
Operations live      HTTP 200
Python compileall    PASS
```

The source-level frontend regression tests are included. The documented environment note is that a production frontend build may be blocked when package installation cannot reach the npm registry.

Run:

```bash
python -m pytest backend/tests -q
python -m pytest copilot/tests -q
cd frontend
npm test
npm run build
```

---

## Team contributions

The original architecture and repository keep a two-person ownership split.

### Harsh — Person 1: Airspace Intelligence Engineer

Primary contribution area:
```text
backend/app/engine/**
backend/app/models/**
backend/data/**
backend/tests/engine/**
```

Built the deterministic airspace intelligence layer, including the digital twin, aircraft/sector/airport/weather/restriction state, route graph and candidate generation, hard-constraint validation, network simulation, stress testing, deterministic metrics, and engine execution/verification behavior.

### Devansh — Person 2: Agent + Product Engineer

Primary contribution area:
```text
copilot/**
frontend/**
backend/app/api/**
backend/tests/api/**
```

Built the agent/product layer, including orchestration and state transitions, investigation/tool adapters, planner/scoring/ranking flow, critic and synthesis, evidence/observability, the human approval/rejection lifecycle, reassessment, API adapters, WebSocket operational feed integration, and the React command-center UI.

Shared coordination lives under:
```text
contracts/**
scenarios/**
docs/**
```

The names above describe the intended implementation ownership reflected by the repository's ownership and plan documents.

---

## Documentation

| Document | Purpose |
|---|---|
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`docs/architecture.md`](docs/architecture.md) | System architecture and boundaries |
| [`docs/agent-system.md`](docs/agent-system.md) | Agent lifecycle, tools, critic, approval and reassessment |
| [`docs/engine.md`](docs/engine.md) | Deterministic engine internals and public facade |
| [`docs/api-reference.md`](docs/api-reference.md) | API endpoints and behavior |
| [`docs/flagship-scenario.md`](docs/flagship-scenario.md) | Scenario timeline and candidate behavior |
| [`docs/live-operations.md`](docs/live-operations.md) | Operational replay and event layer |
| [`docs/demo-guide.md`](docs/demo-guide.md) | Judge demonstration flow |
| [`docs/judging.md`](docs/judging.md) | Judge-facing proof points and talking points |
| [`docs/testing.md`](docs/testing.md) | Test strategy and regression commands |
| [`docs/configuration.md`](docs/configuration.md) | Environment variables and runtime configuration |
| [`docs/limitations-and-safety.md`](docs/limitations-and-safety.md) | Safety boundary and limitations |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common local issues |
| [`OWNERSHIP.md`](OWNERSHIP.md) | Contribution boundaries |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution workflow |

---

## Project thesis

AERIS is built around one operational question:

> **Can we improve one flight without quietly making the surrounding network worse?**

The project answers that question with a deterministic operational model, network-aware evaluation, future stress testing, adversarial challenge, explicit human control and post-action verification.
