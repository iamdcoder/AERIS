# AERIS Testing Strategy

## 1. Testing goals

Testing is designed around the decision lifecycle rather than around individual helper functions only.

The most important properties are:

- deterministic behavior;
- stable candidate identity;
- hard-constraint correctness;
- correct network simulation;
- stress-test repeatability;
- critic behavior;
- human-approval enforcement;
- rejection/reassessment correctness;
- verification correctness;
- API transport correctness;
- graceful degraded behavior.

---

## 2. Test organization

```text
backend/tests/
├── api/
├── engine/
└── integration/

copilot/tests/
├── agent/
├── test_agent.py
├── test_engine_client.py
├── test_failure_modes.py
├── test_gemini.py
├── test_guardrails.py
├── test_hybrid.py
├── test_planner.py
└── test_tools.py
```

---

## 3. Backend test coverage

The backend suite covers:

```text
API behavior
constraint validation
digital-twin progression
flagship scenario
public engine facade
route generation
network simulation
stress testing
metrics
integration
```

Current verified result:

```text
286 passed
```

---

## 4. Copilot test coverage

The copilot suite covers:

```text
approval controller
critic
lifecycle controller
planner
ranker
real-engine orchestration
reassessment
scoring
synthesizer
agent orchestration
engine adapter
failure modes
Gemini integration
field guardrails
hybrid investigation
tool registry
```

Current verified result:

```text
123 passed, 5 skipped
```

---

## 5. Frontend verification

The frontend currently uses Vite.

Production build check:

```bash
cd frontend
npm run build
```

The release artifact intentionally excludes `node_modules/` and `dist/`. The package manifest and lockfile are pinned; run `npm ci` followed by `npm run build` from `frontend/`. A fresh build was not re-run in this review environment because dependency installation timed out.

---

## 6. Recommended regression commands

From repository root:

```bash
python -m pytest backend/tests -q
python -m pytest copilot/tests -q
```

Then:

```bash
cd frontend
npm run build
```

Finally, run both deterministic proof scripts:

```bash
cd ..
python scripts/run_flagship.py
python scripts/run_agent_flagship.py
```

---

## 7. Key invariants

### Determinism

Running the flagship scenario twice from a reset baseline should produce equivalent candidate and decision outcomes.

### Candidate identity

A candidate ID such as `ALT-D` must remain stable across:

```text
generation
validation
simulation
stress test
scoring
recommendation
approval
application
verification
```

### Human gate

Execution must never be treated as authorized without explicit approval.

### Reassessment isolation

After rejection:

```text
previous decision state
        !=
new approval-cycle state
```

A previous `EXECUTED` or `VERIFIED` state must not leak into a new pending recommendation.

### Honest degradation

When a tool, LLM, adapter, or verifier fails, the system should report that fact rather than fabricate operational success.

---

## 8. Manual smoke test matrix

| Test | Expected result |
|---|---|
| Fresh page | Baseline loads |
| Run AERIS | Recommendation appears at human gate |
| Inspect candidates | Five candidates shown |
| Inspect invalid routes | ALT-C / ALT-E show rejection reasons |
| Inspect critic | Critic evidence visible |
| Approve ALT-D | Execute then verify |
| Reject ALT-D | Reassessment; fresh approval only if a robust option remains |
| Reject again | Reassess again; fail closed if no robust option remains |
| Refresh after reset | Clean baseline |
| Gemini unavailable | Deterministic fallback, no fabricated success |

---

## 9. Failure modes intentionally tested

The project tests or models these classes of failures:

- unknown tool;
- invalid tool arguments;
- tool execution failure;
- malformed or insufficient investigation evidence;
- Gemini failure;
- Gemini call budget exhaustion;
- no feasible route;
- human rejection;
- verification requiring reassessment;
- stale candidate identity;
- incorrect candidate route origin.

---

## 10. CI recommendation

For future CI, the minimum gate should be:

```text
backend tests
copilot tests
frontend production build
flagship deterministic runner
```

A PR should not merge if the flagship candidate identity, approval semantics or verification boundary becomes nondeterministic.


## 11. Frontend regression test

The dashboard adapter has a dependency-free Node test for event-time rendering and degraded reassessment presentation:

```bash
cd frontend
npm test
```

This test intentionally does not require Vite or React dependencies.
