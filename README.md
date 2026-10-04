# AERIS

## Agentic Airspace Resilience Intelligence System

AERIS is a human-supervised agentic decision-support system for airline OCC/dispatch operations. It evaluates operational interventions against network-wide consequences and uncertain future states in a deterministic simulated airspace.

### Core decision loop

OBSERVE → DETECT → DIAGNOSE → GENERATE → VALIDATE → SIMULATE → STRESS TEST → CRITIC → RECOMMEND → HUMAN APPROVAL → EXECUTE → VERIFY

### Two-person development model

- **Person 1 — Airspace Intelligence Engineer:** deterministic airspace world, aircraft/sector/airport models, routes, hard constraints, network simulation, stress testing and metrics.
- **Person 2 — Agent + Product Engineer:** agent orchestration, tool adapters, APIs, frontend, decision trail, approval UX and verification UI.

The teams work independently through frozen JSON contracts. See `OWNERSHIP.md` and `docs/team-workflow.md`.

### Safety boundary

AERIS is a simulation/prototype for decision support. It does not control aircraft, replace ATC, replace AAI C-ATFM/SKYFLOW, or issue operational clearances.

### First build target

The flagship scenario is the **Mumbai Monsoon Network Disruption**, designed to demonstrate why a locally attractive reroute can be worse than a network-resilient intervention.

### Quick start

Backend:

```text
cd backend
python -m venv .venv
# activate .venv
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```text
cd frontend
npm install
npm run dev
```

Do not commit `.env`, API keys, `node_modules`, virtual environments, caches, or build output.
