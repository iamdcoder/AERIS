# AERIS Winning Build Plan — Two Developers

This plan expands the existing implementation plan into smaller, conflict-free phase gates. The build should be optimized for end-to-end proof, not file count.

## Phase 0 — Joint contract + demo freeze

**Both together — first 45–60 minutes**

Freeze:

- target flight F102
- airspace/sector geometry
- candidate intervention object
- validation result
- simulation result
- stress-test result
- decision score
- approval/rejection states
- verification result
- flagship timeline

**Exit gate:** both developers can independently create a valid mock response.

---

## Phase 1 — Parallel foundation

### Person 1

1. Domain models
2. Baseline data
3. Digital twin state
4. One-minute deterministic tick
5. 30–50 aircraft baseline

### Person 2

1. Mock fixtures
2. Agent state machine shell
3. Frontend dashboard shell
4. Candidate/metrics/evidence components
5. Approval/verification UI shell

**Exit gate:** both sides run independently with no shared code edits.

---

## Phase 2 — Operational feasibility

### Person 1

1. Route graph
2. Candidate generation
3. Weather intersection
4. Fuel reserve check
5. Restriction check
6. Sector/airport capacity
7. Conflict detection
8. Aggregate validator

### Person 2

1. Tool adapters for every engine capability
2. Structured tool-result objects
3. Agent investigation flow
4. Candidate ranking view
5. Failure states

**Exit gate:** a candidate can be deterministically marked feasible/infeasible and the agent can consume that result.

---

## Phase 3 — Network consequences

### Person 1

1. Multi-flight counterfactual simulation
2. Affected-flight tracking
3. Sector utilization timeline
4. Network delay delta
5. Cascade/ripple indicators
6. Decision score

### Person 2

1. Simulation tool
2. Comparison table
3. Network ripple visualization
4. Evidence trail for rejects
5. Score explanation

**Exit gate:** judges can see that the locally shortest candidate can create a worse network outcome.

---

## Phase 4 — Future robustness + critic

### Person 1

Build deterministic perturbations:

- weather +10/+20%
- capacity −10/−20%
- traffic +10/+20%
- temporary restriction
- downstream airport degradation

### Person 2

1. Stress-test tool
2. Critic challenge
3. Critic evidence card
4. Recommendation revision
5. Confidence/uncertainty display

**Exit gate:** the preliminary winner can be challenged and replaced by a more resilient alternative.

---

## Phase 5 — Full integration

**Both together**

Run:

```text
DISRUPTION
→ DETECTION
→ DIAGNOSIS
→ CANDIDATES
→ VALIDATION
→ SIMULATION
→ STRESS TEST
→ CRITIC
→ RECOMMENDATION
→ HUMAN APPROVAL
→ EXECUTE
→ VERIFY
```

No manual file edits during the scenario run.

**Exit gate:** one-button or one-sequence flagship run from baseline to verified outcome.

---

## Phase 6 — Flagship Mumbai Monsoon scenario

Use the timeline in `scenarios/mumbai_weather_crisis.json`.

Design the candidates to be visibly different:

- ALT-A shortest/local optimum
- ALT-B fuel-first
- ALT-C altitude strategy
- ALT-D sector diversification / resilient option
- ALT-E conservative option / deliberately infeasible or dominated depending on engine result

**Exit gate:** the story is reproducible and numerically convincing.

---

## Phase 7 — Failure-mode hardening

### Person 1

- no-feasible-route test
- fuel insufficiency
- restricted airspace
- sector overload
- conflict case
- weather expansion
- deterministic repeatability

### Person 2

- malformed tool output
- agent/API failure
- LLM failure fallback
- rejection path
- WebSocket disconnect
- loading/error states
- verification failure

**Exit gate:** the system fails honestly instead of fabricating success.

---

## Phase 8 — Judge-facing polish

### Person 1

- stabilize numbers
- optimize slow functions
- clean diagnostic evidence
- lock fixtures

### Person 2

- map readability
- recommendation hierarchy
- three-number emphasis
- concise agent activity
- approval/verification prominence

**Never polish by changing the core decision logic.**

---

## Phase 9 — Demo lock

No major features. Only bug fixes, reliability, documentation and backups.

Required backups:

- recorded walkthrough
- screenshots of candidate comparison
- screenshots of critic reversal
- screenshots of verification
- `.env.example`
- clean README

### The three numbers the judge should remember

1. **Target Benefit**
2. **Network Ripple**
3. **Resilience**

### Core judge questions

AERIS should answer with evidence:

- Why not the shortest route?
- What happens when weather worsens?
- What happens to other aircraft?
- Can the agent execute without the human?
