# AERIS Judge Demo Guide

## 1. Objective

The demo should make one idea memorable:

> **AERIS does not optimize one aircraft in isolation. It makes resilient decisions for the network around it.**

The recommended demo length is approximately four to six minutes.

---

## 2. Before the demo

Start the backend:

```bash
PYTHONPATH=backend uvicorn app.api.app:app --reload
```

Start the frontend:

```bash
cd frontend
npm run dev
```

Check the browser dashboard and make sure the backend status indicator is healthy.

For a deterministic judging environment, prefer the known flagship scenario and avoid changing scenario data during the live presentation.

---

## 3. Opening statement

Use the line:

> “A flight can always be rerouted if we only care about that flight. The real question is what that reroute does to everybody else.”

Then identify the target flight F102 and the Mumbai weather disruption.

---

## 4. Show the disruption

Point out:

```text
weather
BOM acceptance degradation
sector pressure
F102 degradation
```

Explain that these constraints interact rather than existing as isolated alerts.

---

## 5. Run AERIS

Click:

```text
RUN AERIS
```

Let the decision pipeline finish through the human-approval boundary.

The operator should see the observable sequence:

```text
OBSERVE
DIAGNOSE
PLAN
EVALUATE
STRESS TEST
CRITIC
RECOMMEND
HUMAN APPROVAL
```

---

## 6. The AHA moment

Show the comparison table and explain:

```text
ALT-A
Local score 0.92
Network +22.03 min
Stress 0/5

ALT-D
Local score 0.63
Network +12.49 min
Stress 4/5
Resilience 0.80
```

Say:

> “ALT-A is what a local optimizer would love. AERIS prefers ALT-D because the surrounding network and future scenarios make it the more resilient decision.”

Then show the critic panel and point to the failure categories it tested.

---

## 7. Human gate

Move to the approval card.

Say:

> “AERIS can recommend. It cannot decide to execute.”

Show:

```text
HUMAN APPROVAL — REQUIRED
EXECUTION — LOCKED
VERIFICATION — PENDING
```

This demonstrates that the model is not an autonomous controller.

---

## 8. Approve path

Click:

```text
APPROVE & EXECUTE
```

Show the transition:

```text
HUMAN APPROVED
EXECUTED
VERIFIED
```

Point out that verification is reported by the deterministic engine rather than inferred from the fact that an API call succeeded.

---

## 9. Optional rejection path

Only use this when a judge asks about disagreement or human override.

1. Rerun the scenario.
2. Reject the recommendation once.
3. Enter a realistic operator reason such as:

```text
Operator requests a different network trade-off.
```

4. Show that the previous candidate becomes rejected.
5. Show that AERIS reassesses.
6. Show that the new recommendation returns to `HUMAN APPROVAL` with execution locked.

The important statement is:

> “Human rejection creates a new decision cycle. AERIS does not silently execute the rejected option.”

---

## 10. Questions and prepared answers

### “Why not choose the shortest route?”

Because shortest local impact is only one objective. In the flagship scenario ALT-A has a higher local score but creates a larger network delay delta and survives none of the five stress cases.

### “What happens if weather changes?”

AERIS stress-tests candidates against deterministic future weather/capacity/traffic/airport perturbations before recommendation.

### “Does the LLM calculate the fuel or conflict data?”

No. Those values come from deterministic engine-backed tools. The model is used for controlled investigation and synthesis.

### “Can the agent execute on its own?”

No. The operator approval boundary is explicit and enforced in the lifecycle/API.

### “Is this real aviation data?”

No. The flagship scenario is synthetic and deterministic. It demonstrates the decision architecture rather than claiming certification or real-world operational authority.

### “What happens if Gemini fails?”

The hybrid path falls back to deterministic investigation rather than fabricating evidence.

---

## 11. Final line

End with:

> “We are not trying to find a route that is merely shortest. We are trying to find the intervention that leaves the network in the strongest state after we account for what could happen next.”
