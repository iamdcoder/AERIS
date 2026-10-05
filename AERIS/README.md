# AERIS

## Agentic Airspace Resilience Intelligence System

AERIS is a **human-supervised agentic decision-support system for aviation operations**. It evaluates intervention choices for a disrupted flight against the effects those choices can create across the surrounding airspace network and against deterministic future-state stress scenarios.

AERIS is deliberately built as a **decision system, not a chatbot and not an autonomous air-traffic controller**. The deterministic airspace engine remains the authority for operational feasibility and simulation. The agent orchestrates investigation, invokes controlled tools, interprets evidence, compares interventions, asks an adversarial critic to challenge the leading option, synthesizes a recommendation, and waits for explicit human approval before execution.

> **Core thesis:** A reroute that is good for one aircraft can still be bad for the network. AERIS tries to select the intervention that is operationally feasible, less disruptive to the surrounding network, and more resilient to future change.

---

## What AERIS does

The flagship system runs the following decision lifecycle:

```text
LIVE AIRSPACE STATE
        |
        v
     OBSERVE
        |
        v
    DIAGNOSE
        |
        v
       PLAN
        |
        v
     EVALUATE
        |
        v
   STRESS TEST
        |
        v
      CRITIC
        |
        v
    RECOMMEND
        |
        v
 HUMAN APPROVAL
        |
        +------------------+
        |                  |
      REJECT             APPROVE
        |                  |
        v                  v
   REASSESS              EXECUTE
        |                  |
        +----->            v
                    VERIFY
                       |
                       v
                    COMPLETE
```

The implementation is intentionally separated into two layers:

1. **Deterministic airspace intelligence**: digital-twin state, route generation, hard constraints, network simulation, stress testing, and scoring.
2. **Agent + product layer**: investigation, tool orchestration, diagnosis, planning, critic, synthesis, approval/rejection lifecycle, evidence presentation, and the command-center UI.

---

## Why the problem matters

Traditional route selection can over-focus on the affected aircraft: shortest path, smallest local delay, or immediate fuel efficiency. In a stressed network, that can be misleading because traffic shifted by one intervention can overload another sector, increase holding, or amplify downstream delay.

AERIS therefore evaluates each intervention along multiple dimensions:

| Dimension | Question |
|---|---|
| Target impact | What happens to the flight we are trying to protect? |
| Network ripple | What delay or pressure does the intervention create elsewhere? |
| Resilience | Does the intervention remain strong when conditions worsen? |
| Fuel safety | Does the route preserve the required reserve margin? |
| Hard constraints | Is the candidate operationally feasible at all? |

The UI intentionally emphasizes three numbers judges should remember:

```text
TARGET BENEFIT
What happens to the target flight

NETWORK RIPPLE
What happens to the surrounding network

RESILIENCE
How well the decision survives future perturbations
```

---

## Flagship scenario

The main proof scenario is the synthetic **Mumbai Monsoon Multi-Constraint Network Crisis**.

```text
Scenario ID      mumbai_weather_crisis_v2
Target           F102 / AI102
Duration         35 simulated minutes
Aircraft         40
Region           Synthetic Mumbai-region airspace
```

The scenario combines:

- convective weather near BOM;
- degraded BOM arrival acceptance;
- aircraft holding;
- sector-capacity pressure;
- F102 operational degradation and fuel pressure;
- temporary airspace restriction;
- multiple deterministic route alternatives;
- counterfactual network simulation;
- five future-state stress scenarios;
- adversarial critic review;
- explicit human approval;
- post-action deterministic verification.

### Flagship result

The deterministic proof runner currently produces the following key result:

```text
Recommendation             ALT-D — sector diversion resilient
Decision score              0.36
Target delay impact         +4.49 min
Network delay delta        +12.49 min
Stress survival             4/5
Future robustness            80%
Re-intervention probability  20%
Candidates generated        5
Candidates rejected         2
Candidates feasible         3
Verification                VERIFIED
```

The crucial comparison is:

```text
ALT-A — locally attractive, not recommendable
Target delay                +0.03 min
Network delta              +22.03 min
Peak sector                 130%
Stress survival              0/5
Re-intervention probability 100%

ALT-D — network-resilient winner
Target delay                +4.49 min
Network delta              +12.49 min
Peak sector                 100%
Stress survival              4/5
Re-intervention probability  20%
```

This is the central AERIS story: **the final network-resilient choice is not the same as the locally strongest choice**.

---

## Live operational data

The flagship scenario is not the only input path.

AERIS includes a deterministic **operational event replay** so the command center can receive changing airspace conditions instead of displaying a static snapshot.

The replay emits normalized events such as:

```text
SURVEILLANCE_UPDATE
WEATHER_UPDATE
SECTOR_CAPACITY_UPDATE
AIRPORT_CAPACITY_UPDATE
TRAFFIC_UPDATE
RESTRICTION_UPDATE
FLIGHT_STATE_UPDATE
SYSTEM_ALERT
```

The frontend receives these events through:

```text
WebSocket /ws/operations
```

with an automatic REST polling fallback through:

```text
GET /operations/live
```

The live feed advances an isolated deterministic operational twin through the T+35 monitoring timeline. The flagship decision point remains T+19. This is intentionally a **simulated operational feed** for the hackathon. It does not claim privileged production access to AAI, airline, ATC or meteorological systems.

The production integration boundary is:

```text
authorized source
      ↓
OperationalEvent
      ↓
OperationalStateStore
      ↓
AERIS deterministic engine
      ↓
agentic decision loop
```

This means future external data adapters can replace the replay without requiring a rewrite of the decision engine or agent layer.

When the simulated feed moves beyond T+19, the dashboard can **reassess current conditions**. AERIS uses that simulation minute to create a fresh authoritative decision snapshot and reruns the existing recommendation pipeline. This demonstrates the intended “conditions change → decision re-check” behavior without claiming production access to live aviation feeds.

---

## Architecture at a glance

```text
                           +----------------------+
                           |     React / Vite     |
                           |  AERIS Command Center|
                           +----------+-----------+
                                      |
                              REST / HTTP + WebSocket
                                      |
                                      v
                           +----------+-----------+
                           |     FastAPI API       |
                           | transport + adapters  |
                           +----------+-----------+
                                      |
                          stable public-engine API
                                      |
                                      v
                    +-----------------+-----------------+
                    |   Deterministic Airspace Engine  |
                    |                                   |
                    | digital twin                      |
                    | constraints                       |
                    | route generation                  |
                    | network simulation                |
                    | stress testing                    |
                    | decision metrics                  |
                    | execution / verification          |
                    +-----------------+-----------------+
                                      ^
                                      |
                               EngineClient
                                      |
                           +----------+-----------+
                           |    AERIS Copilot     |
                           |                      |
                           | orchestrator         |
                           | investigation        |
                           | planning             |
                           | scoring / ranking    |
                           | critic               |
                           | synthesis            |
                           | approval             |
                           | reassessment         |
                           | verification         |
                           +----------+-----------+
                                      |
                                 controlled tools
                                      |
                                      v
                               Gemini function calls
```

### Authority boundary

The deterministic engine is authoritative for operational feasibility and physical/simulation calculations. The agent does **not** calculate fuel, sector capacity, conflict separation, restriction validity, or other safety-critical quantities itself.

The agent is responsible for:

- choosing investigation actions;
- invoking approved tools;
- gathering evidence;
- organizing the decision workflow;
- comparing candidate evidence;
- requesting critic review;
- synthesizing the recommendation;
- explaining the operational trade-offs;
- requesting explicit human approval.

---

## Running the live operational replay

From the repository root:

```bash
python scripts/run_live_replay.py
```

For the browser dashboard, run the backend and frontend separately:

```bash
python -m uvicorn backend.app.api.app:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, then use **START LIVE FEED**. The operational feed advances the deterministic Mumbai scenario minute-by-minute and can replay through the T+35 monitoring point; the flagship decision point remains T+19.

The browser uses WebSocket transport at `/ws/operations` when available and automatically falls back to `/operations/live` polling.

---

## Repository structure

```text
AERIS/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── airspace.py
│   │   │   │   ├── decisions.py
│   │   │   │   └── copilot.py
│   │   │   └── schemas/
│   │   │       └── requests.py
│   │   ├── engine/
│   │   │   ├── digital_twin/
│   │   │   ├── constraints/
│   │   │   ├── routes/
│   │   │   ├── simulation/
│   │   │   ├── stress_test/
│   │   │   ├── metrics/
│   │   │   └── public.py
│   │   └── models/
│   ├── data/
│   └── tests/
│
├── copilot/
│   ├── agent/
│   │   ├── orchestrator.py
│   │   ├── state.py
│   │   ├── investigation.py
│   │   ├── diagnostics.py
│   │   ├── planner.py
│   │   ├── scoring.py
│   │   ├── ranker.py
│   │   ├── critic.py
│   │   ├── synthesizer.py
│   │   ├── approval.py
│   │   ├── reassessment.py
│   │   ├── execution.py
│   │   └── verification.py
│   ├── engine/
│   │   └── client.py
│   ├── llm/
│   │   └── gemini_client.py
│   ├── tools/
│   ├── mock_engine/
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   └── lib/
│   └── package.json
│
├── contracts/
│   ├── api-contract.md
│   ├── *.schema.json
│   └── examples/
│
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

| Layer | Technology | Current role |
|---|---|---|
| Backend | Python | Engine, agent and API implementation |
| API | FastAPI | HTTP API and interactive API documentation |
| Validation / models | Pydantic | Structured request and agent-state models |
| Graph utilities | NetworkX | Route/network graph support |
| Geometry | Shapely | Spatial / weather / route geometry checks |
| Agent model | Gemini API via `google-genai` | Controlled investigation tool calling |
| Agent orchestration | Custom AERIS orchestration layer | Explicit deterministic stage machine |
| Frontend | React + Vite | Command center UI |
| Visualization | Custom SVG | Current airspace schematic map |
| Testing | pytest | Backend + copilot regression suite |
| Contracts | JSON Schema + Markdown | Team integration boundary |

`frontend/package.json` currently declares Deck.gl and Recharts dependencies, but the current airspace screen uses a custom SVG visualization rather than an active Deck.gl/Recharts implementation.

---

## Local setup

### 1. Clone and enter the repository

```bash
git clone <your-repository-url>
cd AERIS
```

### 2. Create a Python virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install backend dependencies

The repository keeps the Python dependency file at the project root:

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the root template:

```text
.env.example → .env
```

Minimum Gemini configuration:

```text
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-2.5-flash
```

For local frontend-to-backend communication:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_OPERATIONS_WS_URL=ws://127.0.0.1:8000/ws/operations
```

The backend exposes `WS /ws/operations` for the simulated operational feed. The frontend prefers WebSocket and automatically falls back to `GET /operations/live` polling. Production deployments can override the WebSocket URL with `VITE_OPERATIONS_WS_URL`.

### 5. Start the backend

From the repository root:

```bash
python -m uvicorn backend.app.api.app:app --reload
```

Windows PowerShell alternative:

```powershell
python -m uvicorn backend.app.api.app:app --reload
```

The backend should be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
```

### 6. Start the frontend

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite serves the dashboard on its configured development port, normally:

```text
http://localhost:5173
```

---

## Running the flagship proof

The repository includes an offline deterministic runner:

```bash
python scripts/run_flagship.py
```

The runner uses `backend/app/engine/public.py`, resets the engine, progresses the synthetic scenario, evaluates candidates, stress-tests them, applies the recommendation after explicit approval in the scripted demonstration, verifies the result, and prints a machine-readable summary.

It does not require Gemini or network access.

---

## API overview

### Read endpoints

```text
GET  /health
GET  /airspace
GET  /flights/{flight_id}
GET  /disruptions
GET  /network/metrics
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

### Copilot endpoints

```text
POST /copilot/investigate
POST /copilot/recommend
POST /copilot/approve
POST /copilot/reject
POST /copilot/reset
```

See [`contracts/api-contract.md`](contracts/api-contract.md) and [`docs/api-reference.md`](docs/api-reference.md) for payload and behavior details.

---

## Copilot behavior

AERIS exposes a controlled tool registry with these capabilities:

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

Gemini is constrained to investigation-safe capabilities through a guarded registry. Execution and verification are application-controlled lifecycle operations and remain behind the human approval boundary.

### Hybrid behavior

`/copilot/recommend` runs the hybrid investigation path. If Gemini cannot be initialized or cannot provide sufficient evidence, AERIS records the degradation and continues through deterministic investigation rather than fabricating a result.

This produces an explicit degraded-mode behavior:

```text
Gemini unavailable / insufficient evidence
                |
                v
     deterministic investigation
                |
                v
       normal decision pipeline
```

---

## Human approval and reassessment

AERIS intentionally separates recommendation from execution.

Before approval:

```text
Recommendation prepared
        |
        v
HUMAN APPROVAL = REQUIRED
        |
        +---- Reject ----> REASSESS
        |
        +---- Approve ---> EXECUTE
```

A rejected candidate is excluded from the next decision cycle. The next recommendation returns to a fresh human-approval state; execution and verification do not inherit the previous cycle's post-action status.

This ensures that a human rejection changes the decision state rather than merely changing a label in the interface.

---

## Observability

The dashboard exposes **observable operational actions**, not hidden chain-of-thought.

The command center can show:

- current stage;
- tool/investigation evidence summaries;
- candidate feasibility;
- target impact;
- network ripple;
- resilience;
- stress survival;
- critic findings;
- local-vs-network decision reversal;
- human approval state;
- execution state;
- verification state;
- scenario timeline.

The UI is intentionally an evidence surface. It should explain what happened and why the recommendation survived the decision pipeline without presenting private model reasoning as if it were an operational log.

---

## Testing and current verification status

At review time, the deterministic Python regression suites pass as follows:

```text
Backend suite : 286 passed
Copilot suite : 123 passed, 5 skipped
Combined      : 409 passed, 5 skipped
Flagship CLI  : SUCCESS / ALT-D / VERIFIED
Agent proof   : SUCCESS / ALT-D / VERIFIED
```

The release artifact intentionally excludes `node_modules/` and `dist/`. The frontend uses the pinned versions recorded in `frontend/package-lock.json`. The source-level frontend regression tests pass in this environment, but the Vite production build is currently blocked because `npm ci` could not complete with the available registry/network access. Run `cd frontend && npm ci && npm run build` on a network-enabled machine before final submission.

Run the suites from the repository root:

```bash
python -m pytest backend/tests -q
python -m pytest copilot/tests -q
```

Then build the frontend:

```bash
cd frontend
npm run build
```

The complete test matrix and failure-mode coverage are documented in [`docs/testing.md`](docs/testing.md).

---

## Safety and scope

AERIS is a **synthetic simulation and decision-support prototype**.

It does not:

- control real aircraft;
- issue ATC clearances;
- replace a dispatcher, ATC controller, airline OCC process, AAI operational system, or certified flight-management system;
- provide certified safety calculations;
- guarantee real-world route legality or operational feasibility;
- consume live aviation data in the current offline flagship proof.

Its aircraft, coordinates, route graph, capacities, weather and timings are synthetic. The system is designed to demonstrate architecture and decision methodology, not to be deployed directly into safety-critical aviation operations.

---

## Documentation map

Start here, then use the topic-specific documents:

| Document | Purpose |
|---|---|
| [`docs/README.md`](docs/README.md) | Documentation index |
| [`docs/architecture.md`](docs/architecture.md) | Full system architecture and boundaries |
| [`docs/agent-system.md`](docs/agent-system.md) | Agent lifecycle, tools, evidence, approval and reassessment |
| [`docs/engine.md`](docs/engine.md) | Deterministic engine internals and public facade |
| [`docs/decision-scoring.md`](docs/decision-scoring.md) | Scoring weights, normalization and ranking |
| [`docs/api-reference.md`](docs/api-reference.md) | HTTP endpoints and request/response behavior |
| [`docs/flagship-scenario.md`](docs/flagship-scenario.md) | Mumbai scenario, timeline and candidate behavior |
| [`docs/demo-guide.md`](docs/demo-guide.md) | Judge demo and recovery scenarios |
| [`docs/testing.md`](docs/testing.md) | Test strategy and regression commands |
| [`docs/configuration.md`](docs/configuration.md) | Environment variables and local configuration |
| [`docs/limitations-and-safety.md`](docs/limitations-and-safety.md) | Honest technical and operational limitations |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common local issues and fixes |
| [`docs/judging.md`](docs/judging.md) | Judge-facing proof points and talking points |
| [`docs/design-decisions.md`](docs/design-decisions.md) | Why AERIS is designed this way |
| [`docs/glossary.md`](docs/glossary.md) | AERIS / aviation terms used in the project |
| [`docs/build-status.md`](docs/build-status.md) | Current implementation status and freeze checklist |

---

## Project philosophy

AERIS is built around one operational question:

> **Can we improve one flight without quietly making the surrounding network worse?**

Everything else — tools, simulation, critic review, stress testing, evidence, approval, verification and the command center — exists to answer that question in a reproducible and inspectable way.
